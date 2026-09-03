import os, sys, sqlite3, tempfile

sys.stdout.reconfigure(encoding='utf-8')

# Use a throwaway DB so the real parlour.db is untouched
TMP = tempfile.mktemp(suffix='.db')
os.environ['DATABASE_URL'] = TMP
os.environ['FLASK_DEBUG'] = '1'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['ADMIN_PASSWORD'] = 'arjun123'

import app as a

failures = []
def check(label, cond):
    print(('PASS' if cond else 'FAIL'), '-', label)
    if not cond:
        failures.append(label)

print('== 1. validate_booking is now fixed ==')
errors, cleaned = a.validate_booking({
    'name': 'Test User', 'phone': '9876543210', 'email': 'a@b.com',
    'service': 'Bridal Makeup', 'date': '2030-01-01', 'time': '10:30', 'notes': 'hi',
})
check('clean phone', cleaned['phone'] == '9876543210')
check('clean notes', cleaned['notes'] == 'hi')
check('no errors', errors == [])

print()
print('== 2. book POST works (SQL fixed) ==')
client = a.app.test_client()
r = client.post('/book', data={
    'name': 'Jane Doe', 'phone': '9876543210', 'email': 'jane@x.com',
    'service': 'Bridal Makeup', 'date': '2030-01-01', 'time': '11:30', 'notes': 'test',
}, follow_redirects=True)
check('book POST 200', r.status_code == 200)
check('flash success shown', 'booking request was received'.lower() in r.get_data(as_text=True).lower())

conn = sqlite3.connect(TMP)
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM bookings').fetchall()
check('booking inserted', len(rows) == 1)
bid = rows[0]['id']
print('   inserted booking id =', bid)

print()
print('== 3. admin login ==')
r = client.get('/admin')
check('login page shown', 'Staff Login' in r.get_data(as_text=True))
r = client.post('/admin', data={'password': 'wrong'}, follow_redirects=True)
check('wrong pw stays on login', 'Staff Login' in r.get_data(as_text=True))
r = client.post('/admin', data={'password': 'arjun123'}, follow_redirects=True)
page = r.get_data(as_text=True)
check('admin dashboard renders', 'Bookings Dashboard' in page)
check('toolbar shows counts', 'Total: 1' in page)
check('Remove button present', '&#128465;' in page or 'Remove' in page)
check('delete form links present', '/api/bookings/1/delete' in page)

print()
print('== 3b. /admin is protected ==')
anon = a.app.test_client()
r = anon.get('/admin')
check('anonymous blocked', 'Staff Login' in r.get_data(as_text=True))
r = anon.post(f'/api/bookings/{bid}/delete')
check('anonymous delete blocked 401', r.status_code == 401)

print()
print('== 3c. cancel button renders for confirmed booking ==')
r = client.post(f'/api/bookings/{bid}/status', data={'status': 'confirmed'}, follow_redirects=True)
r = client.get('/admin')
check('cancel button present for confirmed', 'value="canceled"' in r.get_data(as_text=True))

print()
print('== 4. mark booking canceled (new status) ==')
r = client.post(f'/api/bookings/{bid}/status', data={'status': 'canceled'}, follow_redirects=True)
st = conn.execute('SELECT status FROM bookings WHERE id=?', (bid,)).fetchone()['status']
check('status now canceled', st == 'canceled')

print()
print('== 5. delete a single booking ==')
r = client.post(f'/api/bookings/{bid}/delete', follow_redirects=True)
check('booking deleted', conn.execute('SELECT COUNT(*) c FROM bookings WHERE id=?', (bid,)).fetchone()['c'] == 0)
check('flash removal msg shown', 'was removed' in r.get_data(as_text=True))

print()
print('== 6. clear-canceled bulk action ==')
for i, st in enumerate(['pending', 'confirmed', 'canceled', 'rejected', 'done']):
    conn.execute(
        "INSERT INTO bookings (name, phone, email, service, date, time, notes, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (f'B{i}', '9876543210', '', 'Party Makeup', '2030-02-01', '10:00', '', st, 'now'),
    )
conn.commit()
before = conn.execute('SELECT COUNT(*) c FROM bookings').fetchone()['c']
check('5 rows seeded', before == 5)
r = client.get('/admin')
check('bulk remove form appears (canceled/rejected exist)', '/admin/clear-canceled' in r.get_data(as_text=True))
r = client.post('/admin/clear-canceled', follow_redirects=True)
check('clear-canceled removed 2', conn.execute('SELECT COUNT(*) c FROM bookings').fetchone()['c'] == before - 2)
left = [row['status'] for row in conn.execute('SELECT status FROM bookings')]
check('kept pending/confirmed/done', sorted(left) == sorted(['pending', 'confirmed', 'done']))
conn.close()

print()
print('== 7. main pages still render ==')
for path in ['/', '/book', '/api/services']:
    r = client.get(path)
    check(f'{path} -> {r.status_code}', r.status_code == 200)

os.remove(TMP)
print()
if failures:
    print('RESULT: FAILURES ->', failures)
    sys.exit(1)
print('RESULT: ALL TESTS PASSED')