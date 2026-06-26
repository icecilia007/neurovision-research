How to run

````
Clonar e acessar o diretório
git clone <seu-repo>
cd projeto-formularios

Subir com Docker
docker compose up --build

Criar migração inicial (primeira vez)
docker compose exec backend alembic revision --autogenerate -m "Initial migration"

Aplicar migração
docker compose exec backend alembic upgrade head

Verificar se as tabelas foram criadas
docker compose exec db psql -U postgres -d formularios_db -c "\dt"
