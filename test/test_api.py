import unittest

import httpx

from app.config import load_config
from app.interfaces.api import create_app


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = create_app(
            load_config(
                database_path=":memory:",
                master_email="mestre@http.local",
                master_password="Mestre@123",
                seed=True,
            )
        )
        self.lifespan = self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)

    async def test_interface_authentication_and_admin_route(self):
        health = await self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})

        page = await self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Crônicas do Reino", page.text)
        self.assertIn("Painel do Mestre", page.text)
        self.assertIn('id="admin-catalog-form"', page.text)
        self.assertIn('id="grant-item-form"', page.text)
        script = await self.client.get("/app.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("distribute-attribute", script.text)
        self.assertIn("recover-character", script.text)
        self.assertIn("combat-hud", script.text)
        self.assertIn("combat-items", script.text)

        docs = await self.client.get("/docs")
        self.assertEqual(docs.status_code, 200)

        denied = await self.client.get("/api/characters")
        self.assertEqual(denied.status_code, 401)

        login = await self.client.post(
            "/api/auth/login",
            json={"email": "mestre@http.local", "password": "Mestre@123"},
        )
        self.assertEqual(login.status_code, 200)
        session = login.json()
        self.assertEqual(session["user"]["role"], "ADMINISTRADOR")

        users = await self.client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {session['token']}"},
        )
        self.assertEqual(users.status_code, 200)
        self.assertEqual(len(users.json()), 1)

        race = await self.client.post(
            "/api/admin/catalog/races",
            headers={"Authorization": f"Bearer {session['token']}"},
            json={
                "name": "Gnomo das Colinas",
                "description": "Inventivo, atento e acostumado a viver em comunidades subterrâneas.",
                "modifiers": {
                    "strength": 2,
                    "defense": 3,
                    "agility": -1,
                    "intelligence": 0,
                    "vitality": 3,
                    "charisma": -1,
                },
            },
        )
        self.assertEqual(race.status_code, 201)
        self.assertEqual(race.json()["name"], "Gnomo das Colinas")

    async def test_admin_can_create_and_grant_mana_potion_from_panel_routes(self):
        admin_login = await self.client.post(
            "/api/auth/login",
            json={"email": "mestre@http.local", "password": "Mestre@123"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

        potion = await self.client.post(
            "/api/admin/catalog/items",
            headers=admin_headers,
            json={
                "name": "Poção Experimental de Mana",
                "type": "POCAO",
                "description": "Recupera 30 pontos de mana.",
                "rarity": "COMUM",
                "value": 20,
                "effectHealth": 0,
                "effectEnergy": 30,
                "attackBonus": 0,
                "defenseBonus": 0,
                "requiredClassId": None,
                "minLevel": 1,
            },
        )
        self.assertEqual(potion.status_code, 201)

        registered = await self.client.post(
            "/api/auth/register",
            json={"name": "Pedro", "email": "pedro@rpg.local", "password": "Pedrinho@123"},
        )
        self.assertEqual(registered.status_code, 201)
        player_id = registered.json()["id"]
        player_login = await self.client.post(
            "/api/auth/login",
            json={"email": "pedro@rpg.local", "password": "Pedrinho@123"},
        )
        player_headers = {"Authorization": f"Bearer {player_login.json()['token']}"}

        classes = (await self.client.get("/api/catalog/classes")).json()
        races = (await self.client.get("/api/catalog/races")).json()
        character = await self.client.post(
            "/api/characters",
            headers=player_headers,
            json={"name": "Pedrinho", "classId": classes[0]["id"], "raceId": races[0]["id"]},
        )
        self.assertEqual(character.status_code, 201)
        self.assertEqual(character.json()["playerId"], player_id)

        granted = await self.client.post(
            f"/api/admin/characters/{character.json()['id']}/inventory/{potion.json()['id']}",
            headers=admin_headers,
            json={"quantity": 3},
        )
        self.assertEqual(granted.status_code, 200)
        self.assertEqual(granted.json()["quantity"], 3)

        inventory = await self.client.get(
            f"/api/characters/{character.json()['id']}/inventory",
            headers=player_headers,
        )
        self.assertEqual(inventory.status_code, 200)
        self.assertEqual(inventory.json()[0]["name"], "Poção Experimental de Mana")
        self.assertEqual(inventory.json()[0]["effectEnergy"], 30)


if __name__ == "__main__":
    unittest.main()
