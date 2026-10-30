//go:build permission_poc

package enterprise

// The server rejects production mode and non-loopback metadata for this build.
func permissionPoCCustomRoles() bool { return true }
