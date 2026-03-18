# Executive Travel Assistant — Deployment Scripts

Automated deployment of a travel planning multi-agent system on Amazon Bedrock AgentCore. Deploys a supervisor agent that orchestrates a flight search and booking sub-agent, backed by an MCP gateway connected to AWS Lambda functions and DynamoDB.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Amazon Bedrock AgentCore                       │
│                                                                  │
│  ┌─────────────────────┐       ┌──────────────────────────────┐  │
│  │  supervisor_agent    │──────▶│  flight_agent                │  │
│  │  (Strands SDK)       │ SSM   │  (Strands SDK + MCP Client)  │  │
│  │                      │ ARN   │                              │  │
│  └─────────────────────┘       └──────────┬───────────────────┘  │
│                                           │                      │
└───────────────────────────────────────────┼──────────────────────┘
                                            │ Cognito M2M OAuth2
                                            ▼
                                 ┌─────────────────────┐
                                 │  AgentCore Gateway   │
                                 │  (MCP Protocol)      │
                                 └──────────┬──────────┘
                                            │
                                            ▼
                                 ┌─────────────────────┐
                                 │  Lambda Functions    │
                                 │  (search_flights,    │
                                 │   book_flights,      │
                                 │   search_hotels,     │
                                 │   etc.)              │
                                 └──────────┬──────────┘
                                            │
                                            ▼
                                 ┌─────────────────────┐
                                 │  DynamoDB Tables     │
                                 │  (synthetic data)    │
                                 └─────────────────────┘
```

## Scripts

| Script | Purpose |
|--------|---------|
| `synthetic-data.py` | Creates DynamoDB tables and loads synthetic travel data (flights, hotels, restaurants, attractions, weather) |
| `deploy-gateway.py` | Deploys Lambda functions, Cognito auth (M2M client credentials), IAM roles, and the AgentCore MCP Gateway |
| `register-target.py` | Registers `search_flights` and `book_flights` MCP tool targets against the gateway |
| `travel-assistant.py` | Deploys `flight_agent` and `supervisor_agent` to AgentCore Runtime using the Strands SDK |
| `test-client.py` | Interactive multi-turn client for testing the deployed supervisor agent |
| `cleanup.py` | Tears down all resources in dependency-aware order |
| `frontend/backend.py` | FastAPI server — serves React build and proxies `/api/chat` to the supervisor agent via SSE |
| `frontend/src/App.js` | React chat UI with streaming markdown responses and session management |
| `frontend/package.json` | React app dependencies and build scripts |

## Prerequisites

- Python 3.10+
- AWS CLI configured with credentials that have admin-level access
- `AWS_DEFAULT_REGION` set (defaults to `us-east-1`)
- Lambda zip files present at `../notebooks - v3/travel-mac/lambdas/`

Install dependencies:
```bash
pip install boto3 requests bedrock-agentcore bedrock-agentcore-starter-toolkit strands-agents strands-agents-tools
```

## Deployment Steps

Run scripts in order from the `exec-travel-assistant/` directory:

### Step 1: Load synthetic data
```bash
python synthetic-data.py
```
Creates 5 DynamoDB tables (`exec-synthetic-flights`, `exec-synthetic-hotels`, `exec-synthetic-restaurants`, `exec-synthetic-attractions`, `exec-synthetic-weather`) and populates them with sample travel data.

### Step 2: Deploy the MCP Gateway
```bash
python deploy-gateway.py
```
Creates:
- 7 Lambda functions (flight, hotel, restaurant, attraction, loyalty, reservation, book_flight)
- Lambda execution IAM role (`exec_gateway_lambda_iamrole`)
- Cognito user pool (`exec-agentcore-gateway-pool`), resource server, M2M client
- AgentCore MCP Gateway (`exec-TravellerAppGwforLambda`) with Cognito JWT authorizer
- Gateway IAM role (`agentcore-exec-lambdagateway-role`)

Outputs `config.json` with all resource IDs, ARNs, and Cognito credentials.

### Step 3: Register MCP tool targets
```bash
python register-target.py
```
Registers `search_flights` and `book_flights` tools as Lambda-backed MCP targets on the gateway. Reads gateway ID and Lambda ARNs from `config.json`.

### Step 4: Deploy agents
```bash
python travel-assistant.py
```
Creates:
- IAM roles for both agents (`agentcore-exec-flight_agent-role`, `agentcore-exec-supervisor_agent-role`)
- `flight_agent` — connects to the MCP gateway via Cognito M2M token, exposes `search_flights` and `book_flights` tools
- `supervisor_agent` — orchestrates flight_agent via `bedrock-agentcore:InvokeAgentRuntime` for both flight search and booking, reads sub-agent ARNs from SSM Parameter Store
- SSM parameters (`/agents/flight_agent_arn`, `/agents/supervisor_agent_arn`)
- ECR repositories (auto-created by starter toolkit)

Agent ARNs and role names are merged into `config.json`.

To deploy and run a smoke test:
```bash
python travel-assistant.py --test
```

### Step 5: Test the deployed agents
```bash
python test-client.py
```
Starts an interactive multi-turn conversation with the supervisor agent. Supports:
- Session persistence across turns via `runtimeSessionId`
- Type `new` to start a fresh session
- Type `quit` or `exit` to end

You can also pass an agent ARN directly:
```bash
python test-client.py --agent-arn arn:aws:bedrock-agentcore:us-east-1:123456:runtime/supervisor_agent-XXXXX
```

### Step 6: Cleanup (when done)
```bash
# Preview what will be deleted
python cleanup.py --dry-run

# Delete all resources
python cleanup.py
```
Tears down all resources in dependency-aware order:
1. AgentCore runtime endpoints → agent runtimes (supervisor first)
2. SSM parameters
3. Gateway targets → gateway (waits for target deletion to propagate)
4. Cognito client → resource server → domain → user pool
5. DynamoDB tables
6. Lambda functions → Lambda IAM role
7. Agent IAM roles
8. Gateway IAM role
9. ECR repositories
10. Local files (`_agent_staging/`, `config.json`)

### Step 7: Deploy the frontend

The frontend is a React chat UI backed by a FastAPI server that proxies requests to the supervisor agent with SSE streaming. The backend reads `supervisor_agent_arn` from `config.json` (generated in Step 2/4).

```bash
cd frontend

# Install Python backend dependencies
pip install -r requirements.txt

# Install React dependencies and build
npm install
npm run build

# Start the server (serves React build + /api/chat proxy)
python backend.py
```

Open `http://localhost:8000` in your browser. The app supports multi-turn conversations with session persistence.

To point the React dev server at a different backend (e.g., remote), set `REACT_APP_API_URL`:
```bash
REACT_APP_API_URL=http://<remote-host>:8000 npm start
```

## Agent System Prompts

The agent behavior is controlled by system prompts defined in `travel-assistant.py`:

**flight_agent** — Handles both search and booking via MCP gateway tools:
- Uses `search_flights` to find flights based on origin, destination, dates, and preferences
- Uses `book_flights` to book flights directly without requiring any input parameters (the Lambda is a no-arg stub that returns a confirmation)
- Defaults to one-way, Economy class, current year next month when details are omitted

**supervisor_agent** — Orchestrates the flight agent for both search and booking:
- Delegates all flight queries and booking requests to `call_flight_agent`
- Does not fabricate flight data — always invokes the sub-agent
- Passes booking requests through to the flight agent rather than refusing them

**call_flight_agent tool** — The supervisor's only tool, described as capable of both searching and booking flights so the model routes booking intents correctly.

## Config File

All resource metadata is stored in a single `config.json`:

```
config.json
├── region
├── gateway_id, gateway_url, gateway_role_arn
├── cognito_user_pool_id, cognito_client_id, cognito_client_secret
├── cognito_discovery_url, cognito_scope_string
├── lambda_arns                          ← deploy-gateway.py
├── flight_agent_arn, supervisor_agent_arn
└── flight_role_name, supervisor_role_name  ← travel-assistant.py
```

## AWS Resources Created

| Service | Resources | Naming Pattern |
|---------|-----------|----------------|
| DynamoDB | 5 tables | `exec-synthetic-*` |
| Lambda | 7 functions | `exec_*_lambda` |
| IAM | 4 roles | `agentcore-exec-*-role`, `exec_gateway_lambda_iamrole` |
| Cognito | 1 user pool, 1 resource server, 1 M2M client | `exec-agentcore-gateway-*` |
| AgentCore Gateway | 1 gateway + 2 targets | `exec-TravellerAppGwforLambda`, `exec-FlightMCPTarget`, `exec-BookFlightMCPTarget` |
| AgentCore Runtime | 2 agents + 2 endpoints | `exec_flight_agent`, `exec_supervisor_agent` |
| SSM Parameter Store | 2 parameters | `/agents/flight_agent_arn`, `/agents/supervisor_agent_arn` |
| ECR | 2 repositories | auto-created by starter toolkit |
