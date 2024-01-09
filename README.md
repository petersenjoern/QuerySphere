# QuerySphere
QuerySphere allows automatically ingest links to data from github, arxiv and local pdfs.
You can easily browse and query the data from the webapp.

# Getting Started 
## Running locally
### Backend
1. Install dependencies: poetry install
2. Set environment variables (see env_example file)
3. Start database and services: docker compose up
4. Run python ingest.py to populate the database
5. Start the python API with: 

### Frontend
1. Install dependencies: cd frontend & yarn
2. Run the frontend with yarn dev
3. Open localhost:3000 in your browser