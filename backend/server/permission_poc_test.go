//go:build permission_poc

package server

import (
	"testing"

	"github.com/stretchr/testify/require"
	"google.golang.org/genproto/googleapis/type/expr"

	"github.com/bytebase/bytebase/backend/common"
	"github.com/bytebase/bytebase/backend/component/config"
	storepb "github.com/bytebase/bytebase/backend/generated-go/store"
)

func TestPermissionPoCProfile(t *testing.T) {
	for _, tc := range []struct {
		name    string
		profile *config.Profile
		allowed bool
	}{
		{
			name:    "isolated loopback metadata",
			profile: &config.Profile{Mode: common.ReleaseModeDev, PgURL: "postgresql://poc@127.0.0.1:17882/bytebase_permission_poc"},
			allowed: true,
		},
		{
			name:    "embedded metadata in Docker",
			profile: &config.Profile{Mode: common.ReleaseModeDev, IsDocker: true},
			allowed: true,
		},
		{
			name:    "embedded metadata outside Docker",
			profile: &config.Profile{Mode: common.ReleaseModeDev},
		},
		{
			name:    "production mode",
			profile: &config.Profile{Mode: common.ReleaseModeProd, PgURL: "postgresql://poc@127.0.0.1:17882/bytebase_permission_poc"},
		},
		{
			name:    "embedded metadata in production Docker",
			profile: &config.Profile{Mode: common.ReleaseModeProd, IsDocker: true},
		},
		{
			name:    "remote metadata in Docker",
			profile: &config.Profile{Mode: common.ReleaseModeDev, IsDocker: true, PgURL: "postgresql://poc@db.example.com/bytebase_permission_poc"},
		},
		{
			name:    "non-isolated external metadata in Docker",
			profile: &config.Profile{Mode: common.ReleaseModeDev, IsDocker: true, PgURL: "postgresql://poc@127.0.0.1/production"},
		},
		{
			name:    "SaaS mode",
			profile: &config.Profile{Mode: common.ReleaseModeDev, PgURL: "postgresql://poc@127.0.0.1:17882/bytebase_permission_poc", SaaS: true},
		},
		{
			name:    "embedded metadata in SaaS Docker",
			profile: &config.Profile{Mode: common.ReleaseModeDev, IsDocker: true, SaaS: true},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			err := validatePermissionPoCProfile(tc.profile)
			if tc.allowed {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
}

func TestPermissionPoCListenAddress(t *testing.T) {
	t.Setenv("BB_PERMISSION_POC_CONTAINER", "")
	require.Equal(t, "127.0.0.1:17880", permissionPoCListenAddress(17880))
	t.Setenv("BB_PERMISSION_POC_CONTAINER", "1")
	require.Equal(t, ":17880", permissionPoCListenAddress(17880))
}

func TestPersonalPermissionPolicy(t *testing.T) {
	condition := &expr.Expr{Expression: "request.time < timestamp(\"2026-01-01T01:00:00Z\")"}
	bindings := []*storepb.Binding{{Role: "roles/reader", Members: []string{"group:developers", "user:someone@example.com"}, Condition: condition}}
	policy := personalPermissionPolicy(bindings, "user:dev@example.com")
	require.Equal(t, []string{"user:dev@example.com"}, policy.Bindings[0].Members)
	require.Equal(t, condition, policy.Bindings[0].Condition)
	require.Equal(t, []string{"group:developers", "user:someone@example.com"}, bindings[0].Members)
}
