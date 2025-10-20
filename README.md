# To start application locally
docker compose up --build

# To run migrations locally
docker -u root exec -it divvywonga_web_1 uv run python divvywonga/manage.py migrate