//go:build permission_poc

package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"os"
	"slices"

	"github.com/labstack/echo/v5"
	"github.com/pkg/errors"
	"google.golang.org/protobuf/encoding/protojson"

	"github.com/bytebase/bytebase/backend/api/auth"
	"github.com/bytebase/bytebase/backend/common"
	"github.com/bytebase/bytebase/backend/common/permission"
	"github.com/bytebase/bytebase/backend/component/config"
	storepb "github.com/bytebase/bytebase/backend/generated-go/store"
	v1pb "github.com/bytebase/bytebase/backend/generated-go/v1"
	"github.com/bytebase/bytebase/backend/store"
	"github.com/bytebase/bytebase/backend/utils"
)

func validatePermissionPoCProfile(profile *config.Profile) error {
	if profile.Mode != common.ReleaseModeDev || profile.SaaS {
		return errors.New("permission PoC requires a self-hosted development build")
	}
	if profile.IsDocker && profile.UseEmbedDB() {
		return nil
	}
	metadata, err := url.Parse(profile.PgURL)
	if err != nil || metadata.Scheme != "postgresql" || !isPoCLoopback(metadata.Hostname()) {
		return errors.New("permission PoC requires an explicit loopback PostgreSQL URL")
	}
	if metadata.Path != "/bytebase_permission_poc" {
		return errors.New("permission PoC requires the isolated bytebase_permission_poc metadata database")
	}
	return nil
}

func isPoCLoopback(host string) bool {
	ip := net.ParseIP(host)
	return host == "localhost" || (ip != nil && ip.IsLoopback())
}

func permissionPoCListenAddress(port int) string {
	if os.Getenv("BB_PERMISSION_POC_CONTAINER") == "1" {
		return fmt.Sprintf(":%d", port)
	}
	return fmt.Sprintf("127.0.0.1:%d", port)
}

type selfPermissionSnapshot struct {
	Workspace       string                     `json:"workspace"`
	Roles           []json.RawMessage          `json:"roles"`
	WorkspacePolicy json.RawMessage            `json:"workspacePolicy"`
	ProjectPolicies map[string]json.RawMessage `json:"projectPolicies"`
}

func configurePermissionPoC(s *Server, secret string) {
	authenticator := auth.New(s.store, secret, s.licenseService, s.bus, s.profile)
	s.echoServer.GET("/poc/self-permissions", func(c *echo.Context) error {
		c.Response().Header().Set("Cache-Control", "no-store")
		c.Response().Header().Set("Vary", "Cookie, Authorization")
		token, err := auth.GetTokenFromHeaders(c.Request().Header)
		if err != nil || token == "" {
			return c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthenticated"})
		}
		user, workspace, _, err := authenticator.AuthenticateToken(c.Request().Context(), token)
		if err != nil || user == nil || user.MemberDeleted || workspace == "" {
			return c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthenticated"})
		}
		ctx := context.WithValue(c.Request().Context(), common.WorkspaceIDContextKey, workspace)
		ctx = context.WithValue(ctx, common.UserContextKey, user)
		project := c.QueryParam("project")
		if project != "" {
			projectID, err := common.GetProjectID(project)
			if err != nil {
				return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid project"})
			}
			allowed, err := s.iamManager.CheckPermission(ctx, permission.ProjectsGet, user, workspace, projectID)
			if err != nil {
				return c.JSON(http.StatusInternalServerError, map[string]string{"error": "permission lookup failed"})
			}
			if !allowed {
				return c.JSON(http.StatusForbidden, map[string]string{"error": "permission denied"})
			}
		}
		snapshot, err := s.currentUserPermissionSnapshot(ctx, workspace, project, user)
		if err != nil {
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "permission lookup failed"})
		}
		return c.JSON(http.StatusOK, snapshot)
	})
}

func personalPermissionPolicy(bindings []*storepb.Binding, member string) *v1pb.IamPolicy {
	policy := &v1pb.IamPolicy{}
	for _, binding := range bindings {
		policy.Bindings = append(policy.Bindings, &v1pb.Binding{
			Role: binding.Role, Members: []string{member}, Condition: binding.Condition,
		})
	}
	return policy
}

func (s *Server) currentUserPermissionSnapshot(ctx context.Context, workspace, project string, user *store.UserMessage) (*selfPermissionSnapshot, error) {
	workspaceIAM, err := s.store.GetWorkspaceIamPolicySnapshot(ctx, workspace)
	if err != nil {
		return nil, err
	}
	member := common.FormatPrincipalMember(user.Email, user.Type)
	workspaceBindings := utils.GetUserIAMPolicyBindings(ctx, s.store, workspace, user, workspaceIAM.Policy)
	workspacePolicy := personalPermissionPolicy(workspaceBindings, member)
	workspaceJSON, err := protojson.Marshal(workspacePolicy)
	if err != nil {
		return nil, err
	}
	result := &selfPermissionSnapshot{
		Workspace: "workspaces/" + workspace, Roles: []json.RawMessage{},
		WorkspacePolicy: workspaceJSON, ProjectPolicies: map[string]json.RawMessage{},
	}
	bindings := append([]*v1pb.Binding{}, workspacePolicy.Bindings...)
	if project != "" {
		projectID, err := common.GetProjectID(project)
		if err != nil {
			return nil, err
		}
		projectIAM, err := s.store.GetProjectIamPolicySnapshot(ctx, workspace, projectID)
		if err != nil {
			return nil, err
		}
		ownBindings := utils.GetUserIAMPolicyBindings(ctx, s.store, workspace, user, projectIAM.Policy)
		policy := personalPermissionPolicy(ownBindings, member)
		encoded, err := protojson.Marshal(policy)
		if err != nil {
			return nil, err
		}
		result.ProjectPolicies[project] = encoded
		bindings = append(bindings, policy.Bindings...)
	}
	roleNames := map[string]bool{}
	for _, binding := range bindings {
		roleNames[binding.Role] = true
	}
	names := make([]string, 0, len(roleNames))
	for name := range roleNames {
		names = append(names, name)
	}
	slices.Sort(names)
	for _, name := range names {
		permissions, err := s.iamManager.GetPermissions(ctx, workspace, name)
		if err != nil {
			return nil, err
		}
		values := make([]string, 0, len(permissions))
		for value, enabled := range permissions {
			if enabled {
				values = append(values, string(value))
			}
		}
		slices.Sort(values)
		encoded, err := protojson.Marshal(&v1pb.Role{Name: name, Permissions: values})
		if err != nil {
			return nil, err
		}
		result.Roles = append(result.Roles, encoded)
	}
	return result, nil
}
