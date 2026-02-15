# Implementation

MVP implemented:
1. POST `/projects` -> Node 0
2. POST `/workflows/runs` -> Nodes 0-2 + adapter outputs
3. POST `/workflows/nodes/editorial` -> Node 3 and new version
4. GET `/versions/{project_id}`
5. GET `/platform-outputs/{project_id}`
6. POST `/publishing/jobs` -> immediate published stub
