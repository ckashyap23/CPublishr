# Project Structure

- `backend/src/main.py`: FastAPI entrypoint
- `backend/src/contracts/prd.py`: strict PRD contracts
- `backend/src/api/v1/endpoints/*`: separate testable endpoints
- `backend/src/services/orchestration/*`: Node 0-3 orchestration
- `backend/src/services/platforms/adapters/*`: platform adapters
- `backend/src/services/publishing/service.py`: publish stub service
- `backend/src/db/*`: models, repos, session
- `backend/tests/integration/test_mvp_e2e.py`: end-to-end test
