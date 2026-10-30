//go:build !permission_poc

package server

import (
	"fmt"

	"github.com/bytebase/bytebase/backend/component/config"
)

func validatePermissionPoCProfile(*config.Profile) error { return nil }
func configurePermissionPoC(*Server, string)             {}
func permissionPoCListenAddress(port int) string         { return fmt.Sprintf(":%d", port) }
