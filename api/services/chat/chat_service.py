"""Chat coordination service: translates question to QuerySpec, executes query, and phrases answer."""
import json
import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from api.config import get_settings
from api.db.models import ChatMessage
from api.schemas import ChatResponse, QuerySpec
from api.services.chat.query_builder import QueryBuilder
from api.services.llm.client import LLMClient
from api.services.llm.fake_client import FakeLLMClient
from api.services.llm.oci_client import OCIGenAIClient
from api.services.llm.prompts import ANSWER_WORDING_PROMPT_V1, QUERY_SPEC_PROMPT_V1


def get_default_llm_client() -> LLMClient:
    """Return configured LLM client (OCI if configured, else Fake)."""
    settings = get_settings()
    if settings.oci_config_file and settings.oci_compartment_id:
        try:
            return OCIGenAIClient()
        except Exception:
            return FakeLLMClient()
    return FakeLLMClient()


class ChatService:
    @staticmethod
    def ask(
        db: Session,
        message: str,
        session_id: uuid.UUID | None = None,
        llm_client: LLMClient | None = None,
    ) -> ChatResponse:
        """Process a conversational query: translate to QuerySpec, execute query, wording answer."""
        if session_id is None:
            session_id = uuid.uuid4()

        client = llm_client or get_default_llm_client()

        # 1. Record user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=message.strip(),
            query_spec=None,
        )
        db.add(user_msg)
        db.flush()

        # 2. Translate question into QuerySpec
        today_str = date.today().isoformat()
        query_prompt = (
            QUERY_SPEC_PROMPT_V1
            .replace("{current_date}", today_str)
            .replace("{question}", message.strip())
        )

        query_spec: QuerySpec
        try:
            query_spec, _ = client.generate_json(query_prompt, QuerySpec, prompt_version="1.0")
        except Exception:
            # Fallback for unexpected parse issues
            query_spec = QuerySpec(
                is_refusal=False,
                aggregation="sum",
                direction="debit",
                search=message.strip(),
            )

        # 3. Handle Refusals
        if query_spec.is_refusal:
            refusal_ans = query_spec.refusal_reason or "I can't answer that from your data."
            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=refusal_ans,
                query_spec=query_spec.model_dump(mode="json"),
            )
            db.add(assistant_msg)
            db.commit()

            return ChatResponse(
                session_id=session_id,
                message_id=assistant_msg.id,
                role="assistant",
                answer=refusal_ans,
                filters_used={"Status": "Out of scope"},
                query_spec=query_spec.model_dump(mode="json"),
                created_at=assistant_msg.created_at,
            )

        # 4. Safe Query Execution
        exec_result = QueryBuilder.execute(db, query_spec)

        # 5. Phrasing Answer via LLM
        wording_prompt = (
            ANSWER_WORDING_PROMPT_V1
            .replace("{question}", message.strip())
            .replace("{result_json}", json.dumps(exec_result.to_dict()))
        )

        try:
            wording_res = client.generate(wording_prompt, prompt_version="1.0")
            answer_text = wording_res.text.strip()
        except Exception:
            # Fallback deterministic answer
            if exec_result.aggregation == "sum":
                answer_text = f"Total: ₹{float(exec_result.total_amount or 0):,.2f} across {exec_result.count} transactions."
            elif exec_result.aggregation == "count":
                answer_text = f"Found {exec_result.count} matching transactions."
            else:
                answer_text = f"Found {exec_result.count} transactions matching your query."

        # 6. Record assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=answer_text,
            query_spec=query_spec.model_dump(mode="json"),
        )
        db.add(assistant_msg)
        db.commit()

        return ChatResponse(
            session_id=session_id,
            message_id=assistant_msg.id,
            role="assistant",
            answer=answer_text,
            filters_used=exec_result.filters_used,
            query_spec=query_spec.model_dump(mode="json"),
            created_at=assistant_msg.created_at,
        )

    @staticmethod
    def get_history(db: Session, session_id: uuid.UUID) -> list[dict[str, Any]]:
        """Retrieve conversation history for a given session."""
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        return [
            {
                "id": str(m.id),
                "session_id": str(m.session_id),
                "role": m.role,
                "content": m.content,
                "query_spec": m.query_spec,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
