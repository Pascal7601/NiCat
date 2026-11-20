# NiCat current HTTP contract

The current protocol contract is **[API_CONTRACT_V1.md](API_CONTRACT_V1.md)**, the hand-maintained OpenAPI draft is **[openapi.contract.yaml](openapi.contract.yaml)**, and the client type definitions are **[../frontend-contract/nicat-api.ts](../frontend-contract/nicat-api.ts)**. The prior session-authenticated v0.2 contract is retained for audit in [archive/v0.2_contract.md](archive/v0.2_contract.md). JWT replaces session authentication for all `/api/v1/` endpoints; Django admin still uses sessions.
