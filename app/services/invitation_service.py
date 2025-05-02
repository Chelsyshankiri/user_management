from uuid import UUID
from app.utils.utils_minio import minio_client
from app.models.invite_model import Invitation
from app.database import Database
import qrcode
from io import BytesIO
from qrcode.image.pil import PilImage
from sqlalchemy.ext.asyncio import AsyncSession

async def generate_invitation(inviter_id: UUID, invitee_email: str, db: AsyncSession):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"inviter:{inviter_id}, email:{invitee_email}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)

    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    client = minio_client()
    file_name = f"invites/{invitee_email}.png"
    client.put_object("qrcode-minio-bucket", file_name, img_byte_arr, length=img_byte_arr.getbuffer().nbytes)
    qr_code_url = f"http://minio:9000/qrcode-minio-bucket/{file_name}"

    invitation = Invitation(
        inviter_id=inviter_id,
        invitee_email=invitee_email,
        qr_code_url=qr_code_url
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    return invitation