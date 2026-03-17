import os
from langchain_community.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import DB_PATH

# 模拟清洗后的 JSON 数据
RAW_DATA = [
    {"name": "阿莫西林胶囊", "content": "适应症：呼吸道感染、泌尿道感染。用法：口服,成人一次0.5g。注意：青霉素过敏禁用。"},
    {"name": "布洛芬缓释胶囊", "content": "适应症：缓解头痛、关节痛、发热。用法：口服,成人一次1粒,一日2次。注意：饭后服用。"},
    {"name": "连花清瘟胶囊", "content": "主治：清瘟解毒,宣肺泄热。用于流感高热、肌肉酸痛。用法：一次4粒,一日3次。"}
]

def create_vector_db():
    print("🚀 [Data Service] 开始构建医疗知识库...")

    # 1. 数据结构化
    docs = []
    for item in RAW_DATA:
        text = f"药品：{item['name']}\n说明：{item['content']}"
        docs.append(Document(page_content=text, metadata={"source": "json"}))

    # 2. 文本切分
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(docs)

    # 3. 向量化 (Embedding)
    print("   - 加载 Embedding 模型...")
    embeddings = HuggingFaceEmbeddings(
        model_name="shibing624/text2vec-base-chinese",
        model_kwargs={'device': 'cuda'}
    )

    # 4. 存入 ChromaDB
    print(f"   - 写入向量数据库: {DB_PATH}")
    if os.path.exists(DB_PATH):
        import shutil
        try:
            shutil.rmtree(DB_PATH)
        except:
            pass

    Chroma.from_documents(split_docs, embeddings, persist_directory=DB_PATH)
    print("✅ 知识库构建完成！")

if __name__ == "__main__":
    create_vector_db()