# Authentication & Security Roadmap

## Phase 1 (Current - MVP)
✅ JWT access tokens  
✅ HttpOnly cookie auth  
✅ Refresh tokens  
✅ Environment-based config  

Status: Implemented


## Phase 2 (Post-MVP Security)

### 🔒 Token Rotation
- Store refresh tokens in database
- Revoke old token on every refresh
- Issue new refresh token
- Prevent replay attacks

Status: TODO


### 🔒 Session Invalidation
- Track sessions per device
- Allow logout from all devices
- Auto-revoke on password change
- Admin revoke support

Status: TODO


### 🔒 Device Tracking
- Store device fingerprint
- Store IP + location
- Detect suspicious logins
- Send security alerts

Status: TODO


## Phase 3 (Enterprise Security)
- CSRF protection
- Rate limiting
- IP blacklisting
- MFA / 2FA
- Audit logs

Status: Planned