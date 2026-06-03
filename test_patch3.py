import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as cl:
        # Login as lecturista
        r = await cl.post('/auth/login', json={'email': 'lecturista', 'password': 'lectura123'})
        print('Login:', r.status_code)
        token = r.json()['access_token']

        r2 = await cl.get('/historial-lecturas/', params={'limit': 1}, headers={'Authorization': f'Bearer {token}'})
        print('GET status:', r2.status_code)
        data = r2.json()
        if data:
            id_lectura = data[0]['id_lectura']
            print('Found id_lectura:', id_lectura)

            r3 = await cl.patch(f'/historial-lecturas/{id_lectura}',
                json={'lectura': 123, 'id_novedad': '3'},
                headers={'Authorization': f'Bearer {token}'})
            print('PATCH status:', r3.status_code)
            print('PATCH body:', r3.text[:300])

asyncio.run(main())
