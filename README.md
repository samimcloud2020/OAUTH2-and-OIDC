1. Different Audiences (The Security Boundary)

┌─────────────────┐
                  │   id_token      │  ──> Consumed by Client App (app.js)
                  │ (Authentication)│      Audience: Your App / Frontend
                  └─────────────────┘
 [ Login Server ]
                  ┌─────────────────┐
                  │  access_token   │  ──> Consumed by API / Resource Server (/api/agent)
                  │ (Authorization) │      Audience: Your Backend / Microservices
                  └─────────────────┘
****************************************************************************************************
id_token: The audience (aud claim) is the Client Application (app.js). Its job is to tell the frontend 
          "Here is who just logged in."

access_token: The audience is the Resource Server (API). Its job is to tell backend endpoints "The holder 
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
