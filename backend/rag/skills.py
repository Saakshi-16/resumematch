"""
Backup plan when the AI model is not available: a list of common tech skills.
We detect which skills the job asks for and check whether the resume mentions them.
"""
import re

# skill name -> other ways people write it
SKILLS = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "js"], "TypeScript": ["typescript"],
    "C++": ["c++"], "C#": ["c#"], "Go": ["golang"], "SQL": ["sql"], "R": [],
    "Machine Learning": ["machine learning", "ml"], "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"], "Computer Vision": ["computer vision", "opencv"],
    "LLMs": ["llm", "llms", "large language model", "large language models", "gpt", "gemini", "llama"],
    "RAG": ["rag", "retrieval-augmented generation", "retrieval augmented generation"],
    "Prompt Engineering": ["prompt engineering"],
    "PyTorch": ["pytorch"], "TensorFlow": ["tensorflow"], "Keras": ["keras"], "scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "Hugging Face": ["hugging face", "huggingface", "transformers"],
    "Vector Databases": ["vector database", "vector databases", "faiss", "pinecone", "chromadb", "chroma", "weaviate", "qdrant"],
    "Django": ["django"], "FastAPI": ["fastapi"], "Flask": ["flask"], "REST APIs": ["rest api", "rest apis", "restful"],
    "React": ["react", "react.js", "reactjs"], "Node.js": ["node.js", "nodejs"], "HTML/CSS": ["html", "css"],
    "PostgreSQL": ["postgresql", "postgres"], "MySQL": ["mysql"], "MongoDB": ["mongodb"],
    "Git": ["git", "github"], "Docker": ["docker", "containerize", "containerized"], "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "MLOps": ["mlops", "mlflow", "kubeflow"], "CI/CD": ["ci/cd", "github actions", "jenkins"],
    "Linux": ["linux"], "Data Structures & Algorithms": ["data structures", "algorithms"],
    "Communication": ["communication", "communicate", "presented", "explain"], "Teamwork": ["teamwork", "collaborate", "team"],
}


def _has(text, alias):
    return re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", text) is not None


def find_skills(text):
    low = text.lower()
    return [name for name, aliases in SKILLS.items() if any(_has(low, a) for a in aliases + [name.lower()])]


def aliases_for(skill):
    return SKILLS.get(skill, []) + [skill.lower()]
