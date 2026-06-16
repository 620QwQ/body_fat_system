from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = 'body-fat-system-2024-secret-key'

DATABASE = 'body_fat.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            real_name TEXT NOT NULL,
            nickname TEXT NOT NULL,
            gender TEXT,
            birth_date TEXT,
            height_cm REAL,
            weight_kg REAL,
            goal_type TEXT,
            target_weight_kg REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            profile_name TEXT NOT NULL,
            gender TEXT NOT NULL,
            birth_date TEXT,
            height_cm REAL CHECK(height_cm > 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS body_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            weight_kg REAL CHECK(weight_kg > 0),
            body_fat_pct REAL,
            muscle_mass_kg REAL,
            water_pct REAL,
            note TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE,
            UNIQUE(profile_id, record_date)
        );

        CREATE TABLE IF NOT EXISTS diet_records (
            diet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            meal_time TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            food_name TEXT NOT NULL,
            portion_g REAL,
            calories_kcal REAL,
            protein_g REAL,
            fat_g REAL,
            carb_g REAL,
            FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exercise_records (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            exercise_time TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            duration_min INTEGER CHECK(duration_min > 0),
            calories_burned REAL,
            FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS goals (
            goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            goal_type TEXT NOT NULL,
            target_weight_kg REAL,
            target_body_fat_pct REAL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            is_achieved INTEGER DEFAULT 0,
            FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS food_library (
            food_id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT NOT NULL,
            category TEXT,
            calories_per_100g REAL,
            protein_per_100g REAL,
            fat_per_100g REAL,
            carb_per_100g REAL,
            scene TEXT
        );

        CREATE TABLE IF NOT EXISTS check_ins (
            check_id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            check_date TEXT NOT NULL,
            check_type TEXT NOT NULL,
            is_done INTEGER DEFAULT 1,
            note TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS friendships (
            friendship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (friend_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(user_id, friend_id)
        );

        CREATE TABLE IF NOT EXISTS knowledge_articles (
            article_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            publish_date TEXT DEFAULT (date('now')),
            encouragement TEXT
        );

        CREATE TABLE IF NOT EXISTS exercise_library (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_name TEXT NOT NULL,
            category TEXT,
            calories_per_30min REAL,
            intensity TEXT,
            scene TEXT
        );
    ''')

    # 插入初始数据（如果为空）
    if c.execute("SELECT COUNT(*) FROM food_library").fetchone()[0] == 0:
        foods = [
            ('米饭', '主食', 116, 2.6, 0.3, 25.9, '食堂'),
            ('馒头', '主食', 223, 7.0, 1.1, 44.2, '食堂'),
            ('面条', '主食', 137, 4.5, 0.5, 27.0, '食堂'),
            ('鸡蛋', '蛋白质', 144, 13.3, 8.8, 2.8, '食堂'),
            ('鸡胸肉', '蛋白质', 133, 31.0, 1.2, 0, '食堂'),
            ('红烧肉', '肉类', 395, 14.6, 37.0, 3.1, '食堂'),
            ('炒青菜', '蔬菜', 45, 2.0, 2.5, 4.0, '食堂'),
            ('番茄炒蛋', '菜品', 85, 4.5, 5.0, 5.5, '食堂'),
            ('麻辣烫', '外卖', 80, 5.0, 3.0, 8.0, '外卖'),
            ('炸鸡', '外卖', 290, 20.0, 18.0, 12.0, '外卖'),
            ('奶茶', '饮品', 65, 0.5, 1.5, 13.0, '饮品'),
            ('可乐', '饮品', 42, 0, 0, 10.6, '饮品'),
            ('面包', '零食', 313, 8.3, 5.1, 58.6, '零食'),
            ('薯片', '零食', 536, 7.0, 35.0, 49.0, '零食'),
            ('苹果', '水果', 53, 0.2, 0.2, 13.8, '水果'),
            ('香蕉', '水果', 93, 1.4, 0.2, 22.0, '水果'),
            ('牛奶', '饮品', 54, 3.0, 3.2, 3.4, '饮品'),
            ('豆浆', '饮品', 31, 3.0, 1.6, 1.2, '食堂'),
            ('饺子', '主食', 240, 9.0, 10.0, 28.0, '食堂'),
            ('沙拉', '轻食', 40, 1.5, 0.5, 8.0, '轻食'),
            ('汉堡', '外卖', 295, 17.0, 14.0, 24.0, '外卖'),
            ('薯条', '零食', 312, 3.4, 15.0, 41.0, '零食'),
            ('玉米', '主食', 112, 4.0, 1.2, 22.8, '食堂'),
            ('红薯', '主食', 86, 1.6, 0.1, 20.1, '食堂'),
            ('三明治', '轻食', 220, 12.0, 8.0, 25.0, '轻食'),
        ]
        c.executemany("INSERT INTO food_library VALUES (NULL,?,?,?,?,?,?,?)", foods)

    if c.execute("SELECT COUNT(*) FROM knowledge_articles").fetchone()[0] == 0:
        articles = [
            ('减脂期该怎么吃？', '减脂期应该控制热量缺口在300-500大卡，保证蛋白质摄入。', '饮食',
             '每一点进步都值得被看见！💪'),
            ('宿舍也能做的运动', '俯卧撑、深蹲、平板支撑，在宿舍就能完成。', '运动', '每一滴汗水都是对未来的投资！'),
            (
            '熬夜对体重的影响', '睡眠不足会导致饥饿素上升，保证7-8小时睡眠。', '作息', '早睡早起，身体会给你最好的回报！🌙'),
            ('奶茶热量大揭秘', '一杯正常糖奶茶约400-500大卡，选择无糖或三分糖。', '饮食',
             '偶尔犒劳自己没关系，但要适度哦！'),
            ('为什么平台期是好事', '平台期说明身体正在重新建立平衡，调整运动方式就能突破。', '心理', '你比想象中更强大！'),
            ('考试周如何保持健康', '准备健康零食，每隔一小时起来活动5分钟。', '校园', '照顾好自己，才能发挥最好的水平！📚'),
            ('科学看待体重波动', '体重每天波动1-2公斤是正常的，关注长期趋势。', '心理', '健康和自信才是最美的！'),
        ]
        c.executemany("INSERT INTO knowledge_articles (title,content,category,encouragement) VALUES (?,?,?,?)",
                      articles)

    if c.execute("SELECT COUNT(*) FROM exercise_library").fetchone()[0] == 0:
        exercises = [
            ('慢跑', '有氧', 200, '中', '操场'),
            ('快走', '有氧', 120, '低', '户外'),
            ('跳绳', '有氧', 300, '高', '宿舍'),
            ('篮球', '球类', 250, '中', '操场'),
            ('羽毛球', '球类', 180, '中', '操场'),
            ('健身操', '有氧', 220, '中', '宿舍'),
            ('俯卧撑', '力量', 150, '中', '宿舍'),
            ('深蹲', '力量', 170, '中', '宿舍'),
            ('平板支撑', '核心', 130, '中', '宿舍'),
            ('仰卧起坐', '核心', 160, '中', '宿舍'),
            ('瑜伽', '柔韧', 100, '低', '宿舍'),
            ('爬楼梯', '有氧', 280, '高', '宿舍'),
            ('骑行', '有氧', 220, '中', '户外'),
            ('游泳', '有氧', 350, '高', '健身房'),
            ('高强度间歇', '有氧', 400, '高', '宿舍'),
        ]
        c.executemany(
            "INSERT INTO exercise_library (exercise_name,category,calories_per_30min,intensity,scene) VALUES (?,?,?,?,?)",
            exercises)

    conn.commit()
    conn.close()


# 初始化数据库
with app.app_context():
    init_db()


# 辅助函数
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


def get_age(birth_date):
    if not birth_date: return 0
    try:
        bd = datetime.strptime(birth_date, '%Y-%m-%d')
        today = date.today()
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    except:
        return 0


def profile_status(profile_id):
    conn = get_db()
    row = conn.execute('''
        SELECT p.profile_id, p.profile_name, p.gender, p.height_cm,
               br.record_date, br.weight_kg, br.body_fat_pct,
               br.muscle_mass_kg, br.water_pct,
               ROUND(br.weight_kg / (p.height_cm/100.0 * p.height_cm/100.0), 1) AS bmi
        FROM profiles p
        LEFT JOIN body_records br ON p.profile_id = br.profile_id
            AND br.record_date = (SELECT MAX(record_date) FROM body_records WHERE profile_id = p.profile_id)
        WHERE p.profile_id = ?
    ''', (profile_id,)).fetchone()
    conn.close()
    return row


# ================== 路由 ==================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        pwd = request.form.get('password', '').strip()
        pwd2 = request.form.get('password2', '').strip()
        real_name = request.form.get('real_name', '').strip()
        nickname = request.form.get('nickname', '').strip()
        if not all([phone, pwd, real_name, nickname]):
            return render_template('register.html', error='所有字段不能为空')
        if pwd != pwd2:
            return render_template('register.html', error='两次密码不一致')
        if not (any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd)):
            return render_template('register.html', error='密码必须包含英文和数字')
        if len(pwd) < 6:
            return render_template('register.html', error='密码至少6位')
        if len(phone) != 11 or not phone.isdigit():
            return render_template('register.html', error='请输入正确的11位手机号')

        conn = get_db()
        if conn.execute("SELECT user_id FROM users WHERE phone=?", (phone,)).fetchone():
            conn.close()
            return render_template('register.html', error='该手机号已被注册')
        try:
            conn.execute("INSERT INTO users (phone,password_hash,real_name,nickname) VALUES (?,?,?,?)",
                         (phone, hash_password(pwd), real_name, nickname))
            conn.commit()
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.close()
            session['new_user_id'] = user_id
            return redirect(url_for('setup_profile'))
        except Exception as e:
            conn.close()
            return render_template('register.html', error=f'注册失败：{e}')
    return render_template('register.html')


@app.route('/setup_profile', methods=['GET', 'POST'])
def setup_profile():
    if 'new_user_id' not in session:
        return redirect(url_for('register'))
    if request.method == 'POST':
        uid = session['new_user_id']
        gender = request.form.get('gender', '男')
        y = request.form.get('year', '')
        m = request.form.get('month', '')
        d = request.form.get('day', '')
        birth = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        height = float(request.form.get('height_cm', 170))
        weight = float(request.form.get('weight_kg', 70))
        goal = request.form.get('goal_type', '保持')
        target = float(request.form.get('target_weight', weight))

        conn = get_db()
        conn.execute(
            "UPDATE users SET gender=?, birth_date=?, height_cm=?, weight_kg=?, goal_type=?, target_weight_kg=? WHERE user_id=?",
            (gender, birth, height, weight, goal, target, uid))
        nick = conn.execute("SELECT nickname FROM users WHERE user_id=?", (uid,)).fetchone()['nickname']
        conn.execute(
            "INSERT OR IGNORE INTO profiles (user_id, profile_name, gender, birth_date, height_cm) VALUES (?,?,?,?,?)",
            (uid, nick, gender, birth, height))
        conn.commit()
        conn.close()
        session['user_id'] = uid
        session['nickname'] = nick
        session.pop('new_user_id', None)
        return redirect(url_for('dashboard'))
    return render_template('setup_profile.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        pwd = request.form.get('password', '').strip()
        if not phone or not pwd:
            return render_template('login.html', error='手机号和密码不能为空')
        conn = get_db()
        user = conn.execute("SELECT user_id, nickname FROM users WHERE phone=? AND password_hash=?",
                            (phone, hash_password(pwd))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['user_id']
            session['nickname'] = user['nickname']
            session['theme'] = 'light'
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='手机号或密码错误')
    return render_template('login.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        real_name = request.form.get('real_name', '').strip()
        new_pwd = request.form.get('new_password', '').strip()
        if not all([phone, real_name, new_pwd]):
            return render_template('forgot_password.html', error='所有字段不能为空')
        conn = get_db()
        user = conn.execute("SELECT user_id FROM users WHERE phone=? AND real_name=?", (phone, real_name)).fetchone()
        if not user:
            conn.close()
            return render_template('forgot_password.html', error='手机号或姓名错误')
        conn.execute("UPDATE users SET password_hash=? WHERE user_id=?", (hash_password(new_pwd), user['user_id']))
        conn.commit()
        conn.close()
        return render_template('login.html', success='密码重置成功！请登录')
    return render_template('forgot_password.html')


@app.route('/profile_center', methods=['GET', 'POST'])
def profile_center():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'update_info':
            nick = request.form.get('nickname', '').strip()
            phone = request.form.get('phone', '').strip()
            gender = request.form.get('gender', '男')
            birth = request.form.get('birth_date', '')
            height = request.form.get('height_cm', '')
            weight = request.form.get('weight_kg', '')
            try:
                conn.execute(
                    "UPDATE users SET nickname=?, phone=?, gender=?, birth_date=?, height_cm=?, weight_kg=? WHERE user_id=?",
                    (nick, phone, gender, birth, height, weight, session['user_id']))
                conn.commit()
                session['nickname'] = nick
                conn.close()
                return render_template('profile_center.html', success='个人信息更新成功')
            except Exception as e:
                conn.close()
                return render_template('profile_center.html', error=f'更新失败：{e}')
        elif action == 'change_password':
            old = request.form.get('old_password', '')
            new = request.form.get('new_password', '')
            new2 = request.form.get('new_password2', '')
            if new != new2:
                conn.close()
                return render_template('profile_center.html', error='两次新密码不一致')
            user = conn.execute("SELECT * FROM users WHERE user_id=? AND password_hash=?",
                                (session['user_id'], hash_password(old))).fetchone()
            if not user:
                conn.close()
                return render_template('profile_center.html', error='原密码错误')
            conn.execute("UPDATE users SET password_hash=? WHERE user_id=?", (hash_password(new), session['user_id']))
            conn.commit()
            conn.close()
            return render_template('profile_center.html', success='密码修改成功！')
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile_center.html', user=user)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session['user_id'],)).fetchone()
    profiles = conn.execute(
        "SELECT profile_id, profile_name, gender, height_cm, birth_date FROM profiles WHERE user_id=? ORDER BY profile_id",
        (session['user_id'],)).fetchall()
    profiles = [dict(p) for p in profiles]
    for p in profiles:
        p['age'] = get_age(p['birth_date']) if p['birth_date'] else 0
        status = profile_status(p['profile_id'])
        if status:
            p['weight_kg'] = status['weight_kg']
            p['body_fat_pct'] = status['body_fat_pct']
            p['bmi'] = status['bmi']
            p['record_date'] = status['record_date']
        else:
            p['weight_kg'] = p['body_fat_pct'] = p['bmi'] = p['record_date'] = None
    conn.close()
    active = profiles[0]['profile_id'] if profiles else 0
    return render_template('dashboard.html', user=user, profiles=profiles, active_profile_id=active)


@app.route('/calorie_table')
def calorie_table():
    return render_template('calorie_table.html')


@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    today = date.today()
    week_ago = today - timedelta(days=7)
    ex = conn.execute('''
        SELECT u.nickname, SUM(e.calories_burned) as total_burn, SUM(e.duration_min) as total_duration
        FROM exercise_records e
        JOIN profiles p ON e.profile_id = p.profile_id
        JOIN users u ON p.user_id = u.user_id
        WHERE e.exercise_time >= ?
        GROUP BY u.user_id
        ORDER BY total_burn DESC LIMIT 10
    ''', (week_ago.strftime('%Y-%m-%d'),)).fetchall()
    ch = conn.execute('''
        SELECT u.nickname, COUNT(c.check_id) as check_count
        FROM check_ins c
        JOIN profiles p ON c.profile_id = p.profile_id
        JOIN users u ON p.user_id = u.user_id
        WHERE c.check_date >= ?
        GROUP BY u.user_id
        ORDER BY check_count DESC LIMIT 10
    ''', (week_ago.strftime('%Y-%m-%d'),)).fetchall()
    conn.close()
    return render_template('leaderboard.html', week_exercise=ex, week_checkin=ch)


@app.route('/friends')
def friends():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    uid = session['user_id']
    # 已接受的好友
    friends = conn.execute('''
        SELECT u.user_id, u.nickname, u.phone FROM friendships f
        JOIN users u ON (CASE WHEN f.user_id=? THEN f.friend_id ELSE f.user_id END) = u.user_id
        WHERE (f.user_id=? OR f.friend_id=?) AND f.status='accepted' AND u.user_id!=?
    ''', (uid, uid, uid, uid)).fetchall()
    # 收到的申请
    received = conn.execute('''
        SELECT u.user_id, u.nickname, u.phone, f.friendship_id, f.created_at
        FROM friendships f JOIN users u ON f.user_id = u.user_id
        WHERE f.friend_id=? AND f.status='pending'
    ''', (uid,)).fetchall()
    # 发出的申请
    sent = conn.execute('''
        SELECT u.user_id, u.nickname, u.phone, f.friendship_id, f.created_at
        FROM friendships f JOIN users u ON f.friend_id = u.user_id
        WHERE f.user_id=? AND f.status='pending'
    ''', (uid,)).fetchall()
    conn.close()
    return render_template('friends.html', friends_list=friends, pending_received=received, pending_sent=sent)


@app.route('/knowledge_page')
def knowledge_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    arts = conn.execute("SELECT * FROM knowledge_articles ORDER BY publish_date DESC LIMIT 10").fetchall()
    conn.close()
    return render_template('knowledge.html', articles=arts)


# API 路由
@app.route('/api/profile/<int:pid>')
def api_profile(pid):
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    conn = get_db()
    profile = conn.execute("SELECT * FROM profiles WHERE profile_id=?", (pid,)).fetchone()
    status = profile_status(pid)
    week = conn.execute(
        "SELECT record_date, weight_kg, body_fat_pct FROM body_records WHERE profile_id=? AND record_date >= date('now','-7 days') ORDER BY record_date",
        (pid,)).fetchall()
    diet = conn.execute(
        "SELECT SUM(calories_kcal) as cal, SUM(protein_g) as prot, SUM(fat_g) as fat, SUM(carb_g) as carb FROM diet_records WHERE profile_id=? AND date(meal_time)=date('now')",
        (pid,)).fetchone()
    ex = conn.execute(
        "SELECT SUM(calories_burned) as burn, SUM(duration_min) as dur FROM exercise_records WHERE profile_id=? AND date(exercise_time)=date('now')",
        (pid,)).fetchone()
    goal = conn.execute(
        "SELECT * FROM goals WHERE profile_id=? AND is_achieved=0 AND date('now')<=end_date ORDER BY end_date LIMIT 1",
        (pid,)).fetchone()
    conn.close()
    return jsonify({
        'profile': dict(profile) if profile else None,
        'status': dict(status) if status else None,
        'week_data': [dict(r) for r in week],
        'today_diet': dict(diet) if diet else {},
        'today_exercise': dict(ex) if ex else {},
        'goal': dict(goal) if goal else None
    })


@app.route('/api/exercise_library')
def api_exercise_lib():
    conn = get_db()
    data = conn.execute("SELECT * FROM exercise_library ORDER BY category, exercise_name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/food_library_all')
def api_food_all():
    cat = request.args.get('category', '')
    conn = get_db()
    if cat:
        data = conn.execute("SELECT * FROM food_library WHERE category=? ORDER BY food_name", (cat,)).fetchall()
    else:
        data = conn.execute("SELECT * FROM food_library ORDER BY category, food_name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/food_categories')
def api_food_cats():
    conn = get_db()
    cats = conn.execute("SELECT DISTINCT category FROM food_library ORDER BY category").fetchall()
    conn.close()
    return jsonify([r['category'] for r in cats])


@app.route('/api/food_search')
def api_food_search():
    q = request.args.get('q', '').strip()
    if not q: return jsonify([])
    conn = get_db()
    data = conn.execute("SELECT * FROM food_library WHERE food_name LIKE ? LIMIT 20", ('%' + q + '%',)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/add_food', methods=['POST'])
def api_add_food():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    name = d.get('food_name', '').strip()
    conn = get_db()
    if conn.execute("SELECT food_id FROM food_library WHERE food_name=?", (name,)).fetchone():
        conn.close()
        return jsonify({'error': '食物已存在'})
    conn.execute(
        "INSERT INTO food_library (food_name,category,calories_per_100g,protein_per_100g,fat_per_100g,carb_per_100g,scene) VALUES (?,?,?,?,?,?,?)",
        (
        name, d.get('category', '自定义'), d.get('calories', 0), d.get('protein', 0), d.get('fat', 0), d.get('carb', 0),
        d.get('scene', '自定义')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/add_diet', methods=['POST'])
def api_add_diet():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO diet_records (profile_id,meal_time,meal_type,food_name,portion_g,calories_kcal,protein_g,fat_g,carb_g) VALUES (?,datetime('now','localtime'),?,?,?,?,?,?,?)",
        (d['profile_id'], d['meal_type'], d['food_name'], d.get('portion', 100), d.get('calories', 0),
         d.get('protein', 0), d.get('fat', 0), d.get('carb', 0)))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/add_exercise', methods=['POST'])
def api_add_exercise():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO exercise_records (profile_id,exercise_time,exercise_type,duration_min,calories_burned) VALUES (?,datetime('now','localtime'),?,?,?)",
        (d['profile_id'], d['exercise_type'], d.get('duration', 0), d.get('calories', 0)))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/edit_profile', methods=['POST'])
def api_edit_profile():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    conn = get_db()
    conn.execute(
        "UPDATE profiles SET profile_name=?, gender=?, birth_date=?, height_cm=? WHERE profile_id=? AND user_id=?",
        (d['profile_name'], d['gender'], d['birth_date'], d['height_cm'], d['profile_id'], session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/add_profile', methods=['POST'])
def api_add_profile():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    conn = get_db()
    conn.execute("INSERT INTO profiles (user_id,profile_name,gender,birth_date,height_cm) VALUES (?,?,?,?,?)",
                 (session['user_id'], d['profile_name'], d.get('gender', '男'), d.get('birth_date', '2000-01-01'),
                  d.get('height_cm', 170)))
    conn.commit()
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({'success': True, 'profile_id': pid})


@app.route('/api/checkin', methods=['POST'])
def api_checkin():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    pid = d.get('profile_id')
    ctype = d.get('check_type', '运动')
    conn = get_db()
    # 检查今天是否已打卡同类
    exist = conn.execute(
        "SELECT check_id FROM check_ins WHERE profile_id=? AND check_date=date('now') AND check_type=?",
        (pid, ctype)).fetchone()
    if exist:
        conn.close()
        return jsonify({'error': '今天已经打过此类型的卡了'})
    conn.execute("INSERT INTO check_ins (profile_id,check_date,check_type) VALUES (?,date('now'),?)", (pid, ctype))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '打卡成功'})


@app.route('/api/set_goal', methods=['POST'])
def api_set_goal():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO goals (profile_id,goal_type,target_weight_kg,start_date,end_date) VALUES (?,?,?,date('now'),?)",
        (d['profile_id'], d['goal_type'], d['target_weight'], d['end_date']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/knowledge')
def api_knowledge():
    conn = get_db()
    art = conn.execute("SELECT * FROM knowledge_articles ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    return jsonify(dict(art) if art else {})


@app.route('/api/search_user')
def api_search_user():
    q = request.args.get('q', '').strip()
    if not q: return jsonify([])
    conn = get_db()
    users = conn.execute(
        "SELECT user_id, nickname, phone FROM users WHERE (phone LIKE ? OR nickname LIKE ?) AND user_id!=? LIMIT 10",
        ('%' + q + '%', '%' + q + '%', session['user_id'])).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route('/api/add_friend', methods=['POST'])
def api_add_friend():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    fid = request.json.get('friend_id')
    if not fid or int(fid) == session['user_id']:
        return jsonify({'error': '不能添加自己'})
    conn = get_db()
    exist = conn.execute(
        "SELECT status FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
        (session['user_id'], fid, fid, session['user_id'])).fetchone()
    if exist:
        conn.close()
        return jsonify({'error': '已经是好友或已发送申请'})
    conn.execute("INSERT INTO friendships (user_id,friend_id,status) VALUES (?,?,'pending')", (session['user_id'], fid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/handle_friend', methods=['POST'])
def api_handle_friend():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    d = request.json
    fid = d.get('friendship_id')
    act = d.get('action')
    conn = get_db()
    if act == 'accept':
        conn.execute("UPDATE friendships SET status='accepted' WHERE friendship_id=? AND friend_id=?",
                     (fid, session['user_id']))
    else:
        conn.execute("DELETE FROM friendships WHERE friendship_id=? AND friend_id=?", (fid, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/delete_friend', methods=['POST'])
def api_delete_friend():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    fid = request.json.get('friend_id')
    conn = get_db()
    conn.execute("DELETE FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
                 (session['user_id'], fid, fid, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/pending_count')
def api_pending_count():
    if 'user_id' not in session: return jsonify({'count': 0})
    conn = get_db()
    cnt = conn.execute("SELECT COUNT(*) as c FROM friendships WHERE friend_id=? AND status='pending'",
                       (session['user_id'],)).fetchone()['c']
    conn.close()
    return jsonify({'count': cnt})


@app.route('/add_record', methods=['POST'])
def add_record():
    if 'user_id' not in session: return jsonify({'error': '未登录'}), 401
    pid = request.form.get('profile_id')
    date = request.form.get('record_date')
    w = request.form.get('weight_kg')
    fat = request.form.get('body_fat_pct', 0)
    conn = get_db()
    # upsert
    conn.execute(
        "INSERT OR REPLACE INTO body_records (profile_id, record_date, weight_kg, body_fat_pct) VALUES (?,?,?,?)",
        (pid, date, w, fat))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/toggle_theme')
def toggle_theme():
    session['theme'] = 'dark' if session.get('theme') == 'light' else 'light'
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)