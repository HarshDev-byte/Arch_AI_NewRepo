# ArchAI Public Shareable Links

## Overview

Added public shareable project links to ArchAI, allowing users to share their completed projects with anyone via a secure, public URL.

## Features Implemented

### ✅ Backend (Python/FastAPI)

**Database Schema:**
- Added `share_token` (TEXT, UNIQUE) to projects table
- Added `is_public` (BOOLEAN, DEFAULT false) to projects table
- Created index on `share_token` for fast lookups

**API Endpoints:**
- `POST /api/projects/{id}/share` - Create shareable link (owner only)
- `DELETE /api/projects/{id}/share` - Revoke shareable link (owner only)  
- `GET /api/projects/shared/{token}` - Public endpoint (no auth required)

**Security:**
- Uses `secrets.token_urlsafe(16)` for cryptographically secure tokens
- Owner-only access for creating/revoking shares
- No sensitive data exposed in public endpoint
- Tokens are unique and unguessable

### ✅ Frontend (Next.js/React)

**ShareButton Component:**
- Public/private status toggle
- One-click copy to clipboard
- QR code generation using `qrcode.react`
- Real-time sharing status
- Professional dark UI with glassmorphism effects

**Public Share Page (`/share/[token]`):**
- No authentication required
- Read-only project view with 3D model
- Project stats (cost, compliance, design score)
- Call-to-action to create own designs
- Responsive design with error handling

**Integration:**
- Added to project page when project is complete
- Passes sharing status from project data
- Handles SSR safely with window object checks

## File Structure

```
backend/
├── migrations/003_shareable_links.sql     # Database migration
├── routes/projects.py                     # Added sharing endpoints
├── schemas/project.py                     # Added sharing fields
├── database.py                           # Updated Project model
└── config.py                             # Added app_url setting

frontend/
├── app/share/[token]/page.tsx            # Public share page
├── components/ShareButton.tsx            # Sharing UI component
└── app/project/[id]/page.tsx            # Integrated ShareButton

scripts/
├── add_sharing_columns.sql              # Simple SQL migration
└── test_sharing.py                      # Functionality tests
```

## Setup Instructions

### 1. Database Migration

Run the SQL migration to add sharing columns:

```sql
-- Option A: Use the migration script
psql -d your_database -f scripts/add_sharing_columns.sql

-- Option B: Run manually
ALTER TABLE projects ADD COLUMN share_token TEXT UNIQUE;
ALTER TABLE projects ADD COLUMN is_public BOOLEAN DEFAULT false;
CREATE INDEX idx_projects_share_token ON projects(share_token);
```

### 2. Environment Variables

Add to your `.env` file:

```bash
APP_URL=http://localhost:3000  # Your frontend URL
```

### 3. Install Dependencies

Frontend QR code package (already installed):

```bash
cd frontend && npm install qrcode.react
```

## Usage

### For Project Owners

1. Complete a project (status = "complete")
2. Scroll to bottom of project page
3. Click "Share" in the Public Sharing section
4. Copy the generated link or show QR code
5. Share the link with anyone

### For Recipients

1. Open the shared link (no login required)
2. View the 3D model, costs, and project details
3. Click "Create My Own Design" to sign up

## API Examples

### Create Share Link

```bash
curl -X POST http://localhost:8000/api/projects/{project_id}/share \
  -H "Cookie: your-auth-cookie"

# Response:
{
  "share_url": "http://localhost:3000/share/abc123def456",
  "token": "abc123def456"
}
```

### Access Shared Project

```bash
curl http://localhost:8000/api/projects/shared/abc123def456

# Response: Full project data (no sensitive fields)
```

### Revoke Share Link

```bash
curl -X DELETE http://localhost:8000/api/projects/{project_id}/share \
  -H "Cookie: your-auth-cookie"

# Response:
{
  "status": "revoked"
}
```

## Security Considerations

- **Secure Tokens:** 16-byte URL-safe tokens (128-bit entropy)
- **Owner Control:** Only project owners can create/revoke shares
- **No Sensitive Data:** Public endpoint excludes user_id, share_token
- **Revocable:** Links can be disabled instantly
- **No Enumeration:** Tokens are unguessable, no sequential IDs

## Testing

Run the test suite:

```bash
python3 scripts/test_sharing.py
```

Tests verify:
- Backend endpoint imports
- Token generation
- Frontend component existence
- Type consistency

## Future Enhancements

- **Expiration Dates:** Add optional link expiration
- **View Analytics:** Track link views and engagement
- **Custom URLs:** Allow custom share slugs
- **Password Protection:** Optional password-protected shares
- **Embed Codes:** Generate iframe embeds for websites

## Implementation Notes

- Uses FastAPI dependency injection for clean separation
- Handles SSR safely with window object checks
- Responsive design works on mobile devices
- QR codes work offline once generated
- Graceful error handling for expired/invalid links

The sharing feature is production-ready and provides a seamless way for ArchAI users to showcase their AI-generated architectural designs publicly.