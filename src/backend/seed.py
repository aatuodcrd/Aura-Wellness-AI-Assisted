import asyncio
import aiohttp
import uuid
import json

BASE_URL = "http://localhost:8000/api/v1"
EMAIL_SUFFIX_LEN = 8

async def create_tenant(session, name):
    async with session.post(f"{BASE_URL}/admin/tenants", json={"name": name}) as resp:
        if resp.status != 200:
            print(f"Failed to create tenant {name}: {await resp.text()}")
            return None
        data = await resp.json()
        print(f"✅ Tenant Created: {name} ({data['id']})")
        return data['id']

async def create_user(session, tenant_id, email, full_name, role, department=None, admin_id=None):
    payload = {
        "tenant_id": tenant_id,
        "email": email,
        "full_name": full_name,
        "role": role,
        "department": department
    }
    headers = {}
    if admin_id:
        headers["X-User-Id"] = str(admin_id)
        
    async with session.post(f"{BASE_URL}/admin/users", json=payload, headers=headers) as resp:
        if resp.status != 200:
             print(f"❌ Failed to create user {email}: {await resp.text()}")
             return None
        data = await resp.json()
        print(f"   👤 User Created: {full_name} ({role}) - ID: {data['id']}")
        return data['id']

async def create_project(session, tenant_id, name, department, admin_id):
    if not admin_id:
        print(f"❌ Cannot create project {name}: missing admin_id")
        return None
    payload = {
         "tenant_id": tenant_id,
         "name": name,
         "department": department
    }
    headers = {"X-User-Id": str(admin_id)}
    async with session.post(f"{BASE_URL}/admin/projects", json=payload, headers=headers) as resp:
        if resp.status != 200:
             print(f"❌ Failed to create project {name}: {await resp.text()}")
             return None
        data = await resp.json()
        print(f"   📂 Project Created: {name} ({department}) - ID: {data['id']}")
        return data['id']

async def upload_document(session, project_id, title, content, user_id):
    if not user_id:
        print(f"      ❌ Upload Failed: missing user_id")
        return
    payload = {
        "title": title,
        "content": content
    }
    headers = {"X-User-Id": str(user_id)}
    async with session.post(f"{BASE_URL}/rag/projects/{project_id}/documents", json=payload, headers=headers) as resp:
        if resp.status == 200:
             print(f"      📄 Document Uploaded: {title}")
        else:
             print(f"      ❌ Upload Failed: {await resp.text()}")

async def seed():
    async with aiohttp.ClientSession() as session:
        # Check integrity
        try:
             async with session.get("http://localhost:8000/health") as resp:
                 if resp.status != 200:
                     print("Backend not healthy")
                     return
        except Exception:
             print("Backend not accessible")
             return

        print("\n🌱 SEEDING DATA FOR 2 TENANTS 🌱\n")

        # --- TENANT A: Acme Corp ---
        print("--- [ 1. Acme Corp ] ---")
        acme_id = await create_tenant(session, "Acme Corp")
        acme_suffix = acme_id.split("-")[0][:EMAIL_SUFFIX_LEN]
        
        # 1. Admin (Bootstrap via Email Hack in API or just create as employee then update? 
        # We assume API allows admin creation for specific emails or we use valid logic. 
        # Using the email backdoor implemented in previous step!)
        acme_admin_id = await create_user(
            session,
            acme_id,
            f"admin+{acme_suffix}@acme.com",
            "Acme Admin",
            "admin",
            "IT",
        )
        
        # 2. Manager
        acme_hr_mgr_id = await create_user(
            session,
            acme_id,
            f"hr_mgr+{acme_suffix}@acme.com",
            "Acme HR Manager",
            "manager",
            "HR",
            acme_admin_id,
        )
        
        # 3. Employee
        acme_emp_id = await create_user(
            session,
            acme_id,
            f"emp+{acme_suffix}@acme.com",
            "Acme Employee",
            "employee",
            "Engineering",
            acme_admin_id,
        )

        # Projects & Docs
        hr_proj_id = await create_project(session, acme_id, "Acme HR Policies", "HR", acme_hr_mgr_id) # Created by Manager
        eng_proj_id = await create_project(session, acme_id, "Acme Eng Specs", "Engineering", acme_admin_id) # Created by Admin
        
        await upload_document(
            session, hr_proj_id, "WFH Policy", 
            "Acme allows remote work 2 days a week.", 
            acme_hr_mgr_id
        )

        # --- TENANT B: Globex Inc ---
        print("\n--- [ 2. Globex Inc ] ---")
        globex_id = await create_tenant(session, "Globex Inc")
        globex_suffix = globex_id.split("-")[0][:EMAIL_SUFFIX_LEN]
        
        globex_admin_id = await create_user(
            session,
            globex_id,
            f"admin+{globex_suffix}@globex.com",
            "Globex Admin",
            "admin",
            "Admin",
        )
        
        globex_mkt_mgr_id = await create_user(
            session,
            globex_id,
            f"mkt_mgr+{globex_suffix}@globex.com",
            "Globex Marketing Mgr",
            "manager",
            "Marketing",
            globex_admin_id,
        )
        
        globex_emp_id = await create_user(
            session,
            globex_id,
            f"emp+{globex_suffix}@globex.com",
            "Globex Jobsworth",
            "employee",
            "Sales",
            globex_admin_id,
        )

        mkt_proj_id = await create_project(session, globex_id, "Globex Campaigns", "Marketing", globex_mkt_mgr_id)
        
        await upload_document(
            session, mkt_proj_id, "Q3 Campaign", 
            "Focus on social media growth for Q3.", 
            globex_mkt_mgr_id
        )

        print("\n✅ Seeding Complete!")
        print("-" * 50)
        print("Use these IDs in your Frontend for testing:")
        print(f"Acme Tenant ID: {acme_id}")
        print(f"  - Admin: {acme_admin_id}")
        print(f"  - HR Mgr: {acme_hr_mgr_id}")
        print(f"  - Employee: {acme_emp_id}")
        print(f"Globex Tenant ID: {globex_id}")
        print(f"  - Admin: {globex_admin_id}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(seed())
