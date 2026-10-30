//go:build permission_poc

package enterprise

// The server restricts this build to self-hosted development and local metadata.
func permissionPoCCustomRoles() bool { return true }
