### 1. Different Audiences (The Security Boundary)

```text
                  ┌─────────────────┐
                  │    id_token     │ ──> Consumed by Client App (app.js)
                  │ (Authentication)│     Audience: Your App / Frontend
                  └─────────────────┘
 [ Login Server ]
                  ┌─────────────────┐
                  │  access_token   │ ──> Consumed by API / Resource Server (/api/agent)
                  │ (Authorization) │     Audience: Your Backend / Microservices
                  └─────────────────┘
****************************************************************************************************
## id_token: The audience (aud claim) is the Client Application (app.js). Its job is to tell the frontend 
          "Here is who just logged in."

## access_token: The audience is the Resource Server (API). Its job is to tell backend endpoints "The holder 
            of this token has permission to access this resource."
*********************************************************************************************
##Opaque Access Tokens vs. Transparent ID Tokens
In modern microservice and API architecture:

The frontend should treat access_token as an OPAQUE string. app.js doesn't need 
(and shouldn't care) what is inside the access token. 
It just blindly attaches it to HTTP headers: Authorization: Bearer <access_token>.

The frontend MUST read the id_token. The id_token is specifically designed as a 
transparent JWT so JavaScript can safely parse it client-side without hitting the backend, 
extracting data like email, name, profile_picture, or roles.

************************************************************************************************
###Lifespans & Expiration Rules
Identity and Access have very different lifespans:

id_token is a "snapshot" of authentication. It proves an event happened at a specific point in time (auth_time). 
It usually expires quickly or is discarded after the frontend creates the user session.

access_token is for short-lived resource access. If access rights or scopes change, access tokens expire quickly 
(e.g., 5 to 15 minutes) and are silently renewed using a refresh_token.

*************************************************************************************************************

###Preventing Security Hazards (Token Misuse / Confused Deputy)
If you use a single token for both API access and user identity:

Information Leakage: To give the frontend user info, your server would have to bake personal details 
(email, user preferences, full name) into the access token. Every downstream microservice, third-party API, 
or logging pipeline that sees the access_token now receives sensitive personal data it doesn't need.

Token Substitution Attacks: If a malicious third-party API receives your access_token, and 
that same token doubles as identity, the malicious API could replay that token back to your 
frontend to impersonate the user.

*********************************************************************************************************

### Token Comparison: `id_token` vs `access_token`

| Feature | `id_token` | `access_token` |
|---|---|---|
| **Purpose** | Identity / Authentication | Permission / Authorization |
| **Protocol** | OpenID Connect (OIDC) | OAuth 2.0 |
| **Who Reads It?** | Client / Frontend (`app.js`) | Resource Server / API (`/api/agent`) |
| **Core Question** | *"Who is the logged-in user?"* | *"What resources can be accessed?"* |
| **Target Audience (`aud`)** | Client Application ID | API Endpoint / Service Identifier |
| **Payload Contents** | User profile (`sub`, `name`, `email`) | Scopes & roles (`read:agent`, `write:prompt`) |
| **Format** | Must be a signed JWT | Opaque string or JWT |
| **Usage** | Decoded client-side to render UI | Sent in `Authorization: Bearer <token>` header |
| **Handling** | Inspected by frontend | Passed along transparently by frontend |

********************************************************************************************************************

### Open in browser:
Go to http://localhost:8000/.

Test the lifecycle:

Click Log In: Calls /token, receives id_token and access_token, saves them to localStorage,
decodes id_token client-side, and shows the profile card.

Refresh the page: localStorage restores the session automatically.

Click Fetch Protected Data: Sends Authorization: Bearer <access_token> to /api/agent and prints the output.

Click Log Out: Clears localStorage and resets the UI.

************************************************************************************************
###Here is the decoded payload from your JWT id_token:

###Decoded Token Header & Payload
### id_token
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqYW11bmEiLCJuYW1lIjoiamFtdW5hIHBhdGVsIiwiZW1haWwiOiJqYW11bmExMDAwQGdtYWlsLmNvbSIsImV4cCI6MTc5MDE4NjIxMX0.2GEFh1jf2YhiCOaPG0JE1jU4Tprl4vXXHJyBgy7mKiY

{
  "Header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "Payload": {
    "sub": "jamuna",
    "name": "jamuna patel",
    "email": "jamuna1000@gmail.com",
    "exp": 1790186211
  }
}


| Field | Value | Meaning |
| :--- | :--- | :--- |
| **`sub`** | `jamuna` | Subject (User ID / Username) |
| **`name`** | `jamuna patel` | Full name of the user |
| **`email`** | `jamuna1000@gmail.com` | User's email address |
| **`exp`** | `1790186211` | Expiration Time (Unix Timestamp) |
**********************************************************************************
###Here is the decoded header and payload for your access_token:

###Decoded Token Header & Payload
### access_token

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqYW11bmEiLCJzY29wZXMiOlsicmVhZDphZ2VudCJdLCJleHAiOjE3OTAxODYyMTF9.aNKJRnk_cMM7AREUOwUbwEe3alnH7g4D56QjbXoApus

{
  "Header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "Payload": {
    "sub": "jamuna",
    "scopes": [                    <------------------------
      "read:agent"
    ],
    "exp": 1790186211
  }
}

| Field | Value | Meaning |
| :--- | :--- | :--- |
| **`sub`** | `jamuna` | Subject (User ID / Username) |
| **`scopes`** | `["read:agent"]` | Granted permissions / scopes |
| **`exp`** | `1790186211` | Expiration Time (Unix Timestamp) |

********************************************************************
# main.py

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: sqlite3.Connection = Depends(get_db)):
    ...
    # OAuth2 Access Token (Authorization)
    access_token = jwt.encode({
        "sub": db_user["username"],
        "scopes": ["read:agent"],  # <--- HERE IS WHERE THE SCOPE IS HARDCODED / GIVEN!
        "exp": now + timedelta(hours=1)
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "id_token": id_token,
        "access_token": access_token,
        "token_type": "bearer"
    }

1. Who gives this permission?
Your FastAPI Auth Server (specifically your POST /token or /login endpoint) issues and grants this permission.

When the client requests an access_token during login, your server checks the user's role or scope request,
signs the JWT with your SECRET_KEY, and bakes ["read:agent"] directly into the token's payload.

| Scope | Permission Level | Allowed Actions |
| :--- | :--- | :--- |
| **`read:agent`** | Read-Only | View agent status, fetch agent response, read logs |
| **`write:agent`** | Read & Write | Create/Update agents, modify settings, delete agents |

**************************************************************************************************

jwt.encode() is the function that generates and cryptographically signs the JWT string on your server.

Without jwt.encode(), your server would just be sending a plain, unverified JSON object over the network that anyone could modify or forge.

What jwt.encode() Does (The 3 Parts)
When you call:

access_token = jwt.encode(
    {"sub": "jamuna", "scopes": ["read:agent"]}, 
    SECRET_KEY, 
    algorithm="HS256"
)

###It takes three pieces of data and turns them into the string you saw (eyJhbGci...):

**Header (Part 1):** Sets the algorithm used (HS256).

**Payload (Part 2):** Converts your Python dictionary (sub, scopes, exp) into Base64-encoded JSON.

**Signature (Part 3):** Takes Parts 1 & 2, runs them through the HS256 hashing algorithm along with your SECRET_KEY,
and generates a unique signature.

jwt.encode() = Base64(Header) + "." + Base64(Payload) + "." + Signature(Header + Payload + SECRET_KEY)
*******************************************************************************************************

### Why is jwt.encode() Necessary?
**1. Tamper Prevention (Tamper-Proofing)**
Anyone can decode the payload of a JWT using Base64 (as we did earlier). However,
no one can change the payload (e.g., changing "sub": "jamuna" to "sub": "admin") without invalidating the Signature created by jwt.encode().

When the request hits /api/agent, jwt.decode() checks the signature against SECRET_KEY. If someone edited the payload, jwt.decode() throws an error and rejects the request.

**2. Stateless Verification**
Because all permissions (scopes), expiration times (exp), and identity details (sub) are signed inside the encoded string:

The client holds the token in localStorage.

The server doesn't need to ask SQLite, "Is Jamuna logged in?" on every single HTTP request.

It simply verifies the signature created by jwt.encode().

**3. Compact Transport**
jwt.encode() compresses the JSON payload into a single, URL-safe string that easily fits inside an HTTP Header (Authorization: Bearer <token>).

**************************************************************************





