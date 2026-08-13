"""Tool definitions for the supervisor agent.

Tools contain no business logic: they parse arguments, call the injected
service, and format the result for the LLM. Logic lives in services/.
"""

from langchain_core.tools import BaseTool, tool

from services.rag_service import RAGService


def build_rag_search_tool(rag_service: RAGService) -> BaseTool:
    """Build the rag_search tool bound to the given RAGService.

    Args:
        rag_service (RAGService): Retrieval use case to delegate to.

    Returns:
        BaseTool: LangChain tool ready to register on the supervisor.
    """

    @tool
    async def rag_search(query: str) -> str:
        """Tìm kiếm trong cơ sở kiến thức của Aduc Auto (chính sách đặt cọc,
        hủy và hoàn tiền, quy trình lái thử, câu hỏi thường gặp về nền tảng).

        Dùng tool này TRƯỚC KHI trả lời mọi câu hỏi về chính sách/quy trình.
        KHÔNG dùng cho câu hỏi cần dữ liệu xe cụ thể (giá, phiên bản, màu).

        Args:
            query: Câu hỏi hoặc từ khóa tiếng Việt cần tra cứu.
        """
        chunks = await rag_service.search_knowledge(query)
        if not chunks:
            return "Không tìm thấy thông tin liên quan trong cơ sở kiến thức."
        return "\n\n---\n\n".join(
            f"[Nguồn: {chunk.source} | score={chunk.score:.3f}]\n{chunk.content}"
            for chunk in chunks
        )

    return rag_search
