"""
Генератор архитектурной диаграммы системы LLM Generator
Требует установки: pip install diagrams
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.framework import Fastapi
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.language import Python
from diagrams.custom import Custom

# Настройки диаграммы
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
}

with Diagram(
    "Архитектура LLM Generator",
    filename="architecture_diagram",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
):
    
    # API Layer
    with Cluster("API Layer (app/api/)"):
        routes = Python("routes.py")
        lit_routes = Python("literature_routes.py")
        rpd_routes = Python("rpd_routes.py")
        api_layer = [routes, lit_routes, rpd_routes]
    
    # Core Layer
    with Cluster("Core Layer (app/core/)"):
        config = Python("config.py")
        db = PostgreSQL("database.py")
        cache = Redis("cache.py")
        model_mgr = Python("model_manager.py\n(LLM)")
        core_layer = [config, db, cache, model_mgr]
    
    # Domain Layer - Literature
    with Cluster("Literature Module (app/literature/)"):
        processor = Python("processor.py\n(PDF, TOC, Offset)")
        embeddings = Python("embeddings.py\n(Векторизация)")
    
    # Domain Layer - Generation
    with Cluster("Generation Module (app/generation/)"):
        gen_v3 = Python("generator_v3.py\n(Многофазная генерация)")
    
    # Domain Layer - RPD
    with Cluster("RPD Module (app/rpd/)"):
        extractor = Python("extractor.py")
        parsers = Python("parsers.py")
        rpd_proc = Python("processor.py")
    
    # Domain Layer - Bot
    with Cluster("Bot Module (app/bot/)"):
        telegram_bot = Python("telegram_bot.py")
    
    # Связи
    lit_routes >> Edge(color="blue") >> processor
    lit_routes >> Edge(color="blue") >> gen_v3
    rpd_routes >> Edge(color="blue") >> extractor
    
    gen_v3 >> Edge(color="green") >> model_mgr
    gen_v3 >> Edge(color="green") >> processor
    gen_v3 >> Edge(color="green") >> embeddings
    
    processor >> Edge(color="orange") >> cache
    telegram_bot >> Edge(color="purple") >> lit_routes

print("✅ Диаграмма создана: architecture_diagram.png")
print("Для использования:")
print("1. pip install diagrams")
print("2. python generate_architecture_diagram.py")
print("3. Откройте architecture_diagram.png")
