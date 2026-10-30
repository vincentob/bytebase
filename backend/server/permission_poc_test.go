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
	valid := config.Profile{Mode: common.ReleaseModeDev, PgURL: "postgresql://poc@127.0.0.1:17882/bytebase_permission_poc"}
	require.NoError(t, validatePermissionPoCProfile(&valid))
	for _, profile := range []*config.Profile{
		{Mode: common.ReleaseModeProd, PgURL: valid.PgURL},
		{Mode: common.ReleaseModeDev, PgURL: "postgresql://poc@db.example.com/bytebase_permission_poc"},
		{Mode: common.ReleaseModeDev, PgURL: "postgresql://poc@127.0.0.1/production"},
		{Mode: common.ReleaseModeDev, PgURL: valid.PgURL, SaaS: true},
	} {
		require.Error(t, validatePermissionPoCProfile(profile))
	}
	require.Equal(t, "127.0.0.1:17880", permissionPoCListenAddress(17880))
}

func TestPersonalPermissionPolicy(t *testing.T) {
	condition := &expr.Expr{Expression: "request.time < timestamp(\"2026-01-01T01:00:00Z\")"}
	bindings := []*storepb.Binding{{Role: "roles/reader", Members: []string{"group:developers", "user:someone@example.com"}, Condition: condition}}
	policy := personalPermissionPolicy(bindings, "user:dev@example.com")
	require.Equal(t, []string{"user:dev@example.com"}, policy.Bindings[0].Members)
	require.Equal(t, condition, policy.Bindings[0].Condition)
	require.Equal(t, []string{"group:developers", "user:someone@example.com"}, bindings[0].Members)
}
