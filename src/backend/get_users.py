import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.db.models import User, Tenant
from app.core.config import settings

async def get_users():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get Tenants
        result = await session.execute(select(Tenant))
        tenants = result.scalars().all()

        print("\n# 🧪 Test Data (Generated)\n")
        
        for tenant in tenants:
            print(f"### Tenant: **{tenant.name}**")
            print(f"- **Tenant ID:** `{tenant.id}`")
            print("\n| Role | Name | Email | User ID | Department |")
            print("| :--- | :--- | :--- | :--- | :--- |")
            
            # Get Users for this Tenant
            users_result = await session.execute(select(User).where(User.tenant_id == tenant.id))
            users = users_result.scalars().all()
            
            for user in users:
                print(f"| {user.role.capitalize()} | {user.full_name} | `{user.email}` | `{user.id}` | {user.department or '-'} |")
            print("\n")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(get_users())
