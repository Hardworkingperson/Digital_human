from langchain_community.llms import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from config import DB_PATH, OLLAMA_URL, OLLAMA_MODEL

class MedicalBrain:
    def __init__(self):
        print(f"🧠 [Brain] 加载向量库: {DB_PATH}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={'device': 'cuda'}
        )
        self.db = Chroma(persist_directory=DB_PATH, embedding_function=self.embeddings, collection_name="medicine_knowledge")
        self.llm = Ollama(base_url=OLLAMA_URL, model=OLLAMA_MODEL, temperature=0.1)
        
        prompt = PromptTemplate(
            template="基于资料回答：{context}\n问题：{question}\n要求：简练专业，60字内。",
            input_variables=["context", "question"]
        )
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm, retriever=self.db.as_retriever(search_kwargs={"k": 2}),
            chain_type_kwargs={"prompt": prompt}
        )
        print("✅ [Brain] 就绪")

    def is_medical_query(self, text):
        """判断是否为医疗健康相关问题"""
        prompt = f"""判断以下问题是否与医疗、健康、药物、疾病、用药、症状相关。
只回答"是"或"否"，不要其他内容。

问题：{text}
回答："""

        try:
            result = self.llm.invoke(prompt).strip()
            is_medical = "是" in result
            print(f"🔍 [Brain] 意图识别: '{text}' -> {'医疗相关' if is_medical else '非医疗'}")
            return is_medical
        except Exception as e:
            print(f"⚠️  [Brain] 意图识别失败: {e}，默认通过")
            return True  # 失败时默认处理，避免漏掉真实需求

    def think(self, text):
        try:
            return self.qa.invoke({"query": text})['result']
        except Exception as e:
            print(f"❌ Brain Error: {e}")
            return "知识库连接异常。"