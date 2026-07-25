# LegacyGuard Frontend Authentication Shell

Implemented:

- React/TypeScript authentication shell
- Login and registration forms
- Backend password-rule validation feedback
- Session-scoped access and refresh token storage
- Authenticated `/auth/me` session restoration
- Automatic bearer-token attachment
- Unauthorized-session clearing
- Logout with backend session revocation
- Protected dashboard shell
- Backend health indicator
- Loading, error, and offline handling
- Responsive styling

Security boundaries:

- Tokens are stored in `sessionStorage`, not permanent local storage.
- Authentication failures do not reveal hidden backend details.
- The frontend does not render the backend `password_hash` field.
- Asset, beneficiary, document, and discovery screens remain placeholders until later milestones.
- No ownership or discovery behavior is implemented client-side; the backend remains authoritative.
