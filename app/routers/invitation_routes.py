from sqlalchemy import select, update
import traceback
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from app.services.invitation_service import generate_invitation
from app.database import Database
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.invite_model import Invitation
from fastapi.responses import RedirectResponse
from app.models.user_model import User
from settings.config import Settings
import base64
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

async def get_db() -> AsyncSession:
    async_session_factory = Database.get_session_factory()
    async with async_session_factory() as session:
        yield session

@router.post("/send-invite/")
async def send_invitation(inviter_id: UUID, invitee_email: str, db: AsyncSession = Depends(get_db)):
    try:
        invitation = await generate_invitation(inviter_id, invitee_email, db)
        return {"message": "Invitation sent successfully!", "data" : invitation}
    except HTTPException as httpexec:
        raise httpexec
    except Exception as e:
        logging.error("Failed to send Invitation:", {str(e)})
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/accept-invite/")
async def accept_invitation(invitee_email: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Invitation).where(Invitation.invitee_email == invitee_email, Invitation.status == "pending")
        )
        invitation = result.scalars().first()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found or already accepted.")

        invitation.status = "accepted"
        await db.execute(update(Invitation).where(Invitation.id == invitation.id).values(status="accepted"))
        await db.commit()
        await db.refresh(invitation)
        

        return {"message": "Invitation accepted successfully!"}

    except Exception as e:
        logger.error(f"Failed to accept invitation: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.get("/redirect/")
async def redirect_invitation(inviter: str, db: AsyncSession = Depends(Database.get_session_factory)):
    """
    Handles QR code scans, marks the invitation as accepted, and redirects the user.
    """
    try:
        decoded_nickname = base64.urlsafe_b64decode(inviter).decode()
        print(decoded_nickname)
        result = await db.execute(select(Invitation).join(User).where(User.nickname == decoded_nickname))
        invitation = result.scalars().first()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid invitation or user not found.")

        if invitation.status != "accepted":
            await db.execute(
                update(Invitation)
                .where(Invitation.id == invitation.id)
                .values(status="accepted")
                )
            await db.commit()

        redirect_url = Settings.Config.BASE_REDIRECT_URL
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"Failed during QR code redirect: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))