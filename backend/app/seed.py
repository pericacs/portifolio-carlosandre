"""Dados fornecidos no pedido, em rascunho. Nunca sobrescreve edições."""
from sqlalchemy.dialects.postgresql import insert
from app.db import get_engine
from app.models import projects, skill_categories

PROJECTS = [
    ("SmartFamily", "smartfamily", "Gestão familiar com IA, integração com WhatsApp e calendário inteligente.", "IA e produtividade", ["FastAPI", "React", "PostgreSQL"]),
    ("Beloria", "beloria", "Plataforma SaaS para salões e barbearias: atendimentos, comissões, financeiro, planos e assinaturas. Arquitetura multi-tenant.", "SaaS", []),
    ("OnStar SCD", "onstar-scd", "Estudo de plataforma fintech para análise de consumo de energia, modelagem de crédito e integração financeira.", "Fintech", []),
    ("Orquestrador IA", "orquestrador-ia", "Orquestração de agentes inteligentes, ferramentas, integrações e workflows para automação de processos empresariais.", "Inteligência Artificial", []),
]
CATEGORIES = ["Dados e Analytics", "Cloud e DevOps", "Arquitetura e Software", "Fintech e Payments", "Inteligência Artificial", "Gestão e Liderança"]


def seed(connection):
    for order, (name, slug, description, category, technologies) in enumerate(PROJECTS):
        connection.execute(insert(projects).values(name=name, slug=slug, description=description,
            category=category, technologies=technologies, sort_order=order, status="draft"
        ).on_conflict_do_nothing(index_elements=["slug"]))
    for order, name in enumerate(CATEGORIES):
        connection.execute(insert(skill_categories).values(name=name, sort_order=order).on_conflict_do_nothing(index_elements=["name"]))


if __name__ == "__main__":
    with get_engine().begin() as connection:
        seed(connection)
    print("Projetos em rascunho e categorias cadastrados. Nenhum conteúdo publicado.")
