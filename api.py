from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()

app = FastAPI(
    title="Neo4j Knowledge Graph API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimpleNeo4jConnector:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def query(self, cypher, params=None):
        with self.driver.session() as session:
            result = session.run(cypher, params or {})
            return [dict(record) for record in result]

    def close(self):
        self.driver.close()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

try:
    neo4j_conn = SimpleNeo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    neo4j_conn.query("RETURN 1 as test")
    print("✅ Connected to Neo4j successfully")
except Exception as e:
    print(f"❌ Failed to connect to Neo4j: {e}")
    neo4j_conn = None

try:
    llm = ChatAnthropic(
        model="claude-opus-4-5-20251101",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0
    )
    print("✅ Connected to Anthropic successfully")
except Exception as e:
    print(f"❌ Failed to connect to Anthropic: {e}")
    llm = None

class CustomKnowledgeGraph:
    def __init__(self, neo4j_conn, llm):
        self.neo4j_conn = neo4j_conn
        self.llm = llm
        self.schema_cache = None

    def get_schema(self):
        if self.schema_cache is None:
            self.schema_cache = self._build_schema()
        return self.schema_cache

    def _build_schema(self):
        schema_parts = []

        try:
            labels = self.neo4j_conn.query("CALL db.labels()")
            node_labels = [record['label'] for record in labels]

            for label in node_labels:
                props_query = f"MATCH (n:{label}) RETURN keys(n) as properties LIMIT 1"
                props_result = self.neo4j_conn.query(props_query)
                properties = props_result[0]['properties'] if props_result else []
                schema_parts.append(f"Node({label}): {', '.join(properties)}")
        except Exception as e:
            schema_parts.append("Node information unavailable")

        try:
            rels = self.neo4j_conn.query("CALL db.relationshipTypes()")
            rel_types = [record['relationshipType'] for record in rels]

            for rel_type in rel_types:
                props_query = f"MATCH ()-[r:{rel_type}]->() RETURN keys(r) as properties LIMIT 1"
                try:
                    props_result = self.neo4j_conn.query(props_query)
                    properties = props_result[0]['properties'] if props_result else []
                    schema_parts.append(f"Relationship[{rel_type}]: {', '.join(properties)}")
                except:
                    schema_parts.append(f"Relationship[{rel_type}]: no properties")
        except Exception as e:
            schema_parts.append("Relationship information unavailable")

        return "\\n".join(schema_parts)

    def generate_cypher(self, question):
        schema = self.get_schema()

        cypher_prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template="""
                You are a Neo4j expert. Generate a Cypher query to answer the question based on the schema.

                Schema:
                {schema}

                Question: {question}

                Rules:
                1. Use only the node labels and properties shown in the schema
                2. Use only the relationship types shown in the schema
                3. Return a valid Cypher query that will answer the question
                4. If asking about multiple entities, use appropriate aggregation
                5. ONLY return the Cypher query, no explanations

                Cypher Query:"""
        )

        formatted_prompt = cypher_prompt.format(schema=schema, question=question)
        response = self.llm.invoke(formatted_prompt)

        cypher_query = response.content.strip()
        if cypher_query.startswith("```"):
            lines = cypher_query.split("\\n")
            cypher_query = "\\n".join(line for line in lines if not line.startswith("```"))

        return cypher_query.strip()

    def answer_question(self, question):
        try:
            cypher_query = self.generate_cypher(question)
            results = self.neo4j_conn.query(cypher_query)

            answer_prompt = PromptTemplate(
                input_variables=["question", "cypher_query", "results"],
                template="""

                Based on the Cypher query results, provide a natural language answer to the question.

                Question: {question}
                Cypher Query: {cypher_query}
                Results: {results}

                Provide a clear, concise answer based on the results:"""
            )

            formatted_prompt = answer_prompt.format(
                question=question,
                cypher_query=cypher_query,
                results=str(results)
            )

            response = self.llm.invoke(formatted_prompt)

            return {
                "answer": response.content,
                "cypher_query": cypher_query,
                "raw_results": results
            }

        except Exception as e:
            return {
                "error": str(e),
                "cypher_query": cypher_query if 'cypher_query' in locals() else None
            }

knowledge_graph = None
if neo4j_conn and llm:
    knowledge_graph = CustomKnowledgeGraph(neo4j_conn, llm)
    print("✅ Neo4j Knowledge Graph API system ready")

@app.get("/")
def root():
    return {"message": "Neo4j Knowledge Graph API", "status": "running"}

@app.get("/health")
def health_check():
    return {
        "neo4j_connected": neo4j_conn is not None,
        "anthropic_connected": llm is not None,
        "knowledge_graph_ready": knowledge_graph is not None
    }

@app.get("/query")
def query_graph(q: str = Query(..., description="Ask a question")):
    if not knowledge_graph:
        return {"error": "Knowledge Graph system not available. Check /health"}

    try:
        result = knowledge_graph.answer_question(q)
        return {"query": q, **result}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
