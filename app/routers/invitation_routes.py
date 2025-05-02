from sqlalchemy import select
import traceback
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from app.services.invitation_service import generate_invitation
from app.database import Database
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.invite_model import Invitation

router = APIRouter()

async def get_db() -> AsyncSession:
    async_session_factory = Database.get_session_factory()
    async with async_session_factory() as session:
        yield session

@router.post("/send-invite/")
async def send_invitation(inviter_id: UUID, invitee_email: str, db: AsyncSession = Depends(get_db)):
    try:
        invitation = await generate_invitation(inviter_id, invitee_email, db)
        return {"message": "Invitation sent successfully!", "qr_code_url": invitation.qr_code_url}
    except HTTPException as httpexec:
        raise httpexec
    except Exception as e:
        print("Error Traceback:", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/accept-invite/")
async def accept_invitation(invitee_email: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Invitation).where(Invitation.invitee_email == invitee_email)
        )
        invitation = result.scalars().first()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found.")

        invitation.status = "accepted"
        await db.commit()
        await db.refresh(invitation)

        return {"message": "Invitation accepted successfully!"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")