import logging
import json
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# 🔹 Настройка логов
logging.basicConfig(level=logging.INFO)

# 🔹 Токен бота
TOKEN = "7805348721:AAE8rvXimHNzHVmYS_-0p_mssgDMke4ZJ00"  # Ваш токен

# 🔹 Создание бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# 🗃️ Загрузка данных из JSON и создание маппинга дисциплин
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(BASE_DIR, "disciplines.json"), "r", encoding="utf-8") as f:
        disciplines_data = json.load(f)
    logging.info(f"JSON загружен: {len(disciplines_data)} курсов")
except FileNotFoundError:
    logging.error(f"Файл disciplines.json не найден в {BASE_DIR}!")
    disciplines_data = {}
except json.JSONDecodeError:
    logging.error("Файл disciplines.json содержит невалидный JSON!")
    disciplines_data = {}

# Создаём маппинг дисциплин с уникальными ID
discipline_map = {}
discipline_id_counter = 0
for course_key, course_data in disciplines_data.items():
    for semester_key, semester_data in course_data.items():
        for discipline_name in semester_data.keys():
            discipline_map[str(discipline_id_counter)] = (course_key, semester_key, discipline_name)
            discipline_id_counter += 1
logging.info(f"Создано {len(discipline_map)} записей в маппинге дисциплин")

# 📝 Класс для состояний FSM
class StudyNavigation(StatesGroup):
    waiting_for_course = State()
    waiting_for_semester = State()
    waiting_for_discipline = State()
    waiting_for_search_query = State()

# 📚 Функция для создания клавиатуры дисциплин
def create_disciplines_keyboard(course: str, semester: str) -> InlineKeyboardMarkup | None:
    logging.info(f"Создание клавиатуры: course={course}, semester={semester}")
    disciplines = disciplines_data.get(course, {}).get(semester, {})
    logging.info(f"Найдено дисциплин: {len(disciplines)}")
    if not disciplines:
        logging.warning(f"Нет данных для {course}, {semester}")
        return None
    buttons_list = []
    for discipline_name, literature in disciplines.items():
        if literature:  # Показываем только дисциплины с литературой
            # Находим ID дисциплины в маппинге
            discipline_id = next(
                key for key, (c, s, d) in discipline_map.items()
                if c == course and s == semester and d == discipline_name
            )
            buttons_list.append([InlineKeyboardButton(
                text=discipline_name,
                callback_data=f"discipline_{discipline_id}"
            )])
    if not buttons_list:
        logging.warning(f"Клавиатура пуста для {course}, {semester}")
        return None
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons_list, row_width=2)
    return keyboard

# 📖 Функция для отображения литературы
async def show_recommended_literature(callback: CallbackQuery, course: str, semester: str, discipline: str):
    literature = disciplines_data.get(course, {}).get(semester, {}).get(discipline, [])
    logging.info(f"Литература для {discipline}: {literature}")
    if literature:
        response_text = f"📚 Рекомендуемая литература по дисциплине: <b>{discipline}</b>\n\n"
        for book in literature:
            response_text += f"📖 <a href=\"{book['url']}\">{book['title']}</a>"
            author_key = 'authors' if 'authors' in book else 'author'
            if book.get(author_key):
                response_text += f" ({book[author_key]})"
            response_text += "\n"
        await callback.message.answer(response_text, disable_web_page_preview=True)
    else:
        await callback.message.answer("❌ Рекомендованная литература для данной дисциплины не найдена.")

# 1️⃣ Главное меню
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(text="📘 Рекомендуемая литература", callback_data="recommended_literature")],
        [InlineKeyboardButton(text="🔍 Поиск дисциплины", callback_data="search_discipline")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])
    await message.answer(
        """👋 Привет!
Я — Telegram-бот BookRecBot 📚

Помогаю студентам-лингвистам быстро находить рекомендованную учебную литературу по дисциплинам.

Выберите уровень или дисциплину, чтобы получить список книг с прямыми ссылками на ЭБС, PDF или онлайн-ресурсы.

🛠 Введите /help для инструкции или /about чтобы узнать больше о проекте.""",
        reply_markup=keyboard
    )

# 2️⃣ Раздел "Рекомендуемая литература"
@dp.callback_query(F.data == "recommended_literature")
async def recommended_literature_handler(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(text="1 курс", callback_data="course=1")],
        [InlineKeyboardButton(text="2 курс", callback_data="course=2")],
        [InlineKeyboardButton(text="3 курс", callback_data="course=3")],
        [InlineKeyboardButton(text="4 курс", callback_data="course=4")]
    ])
    await callback.message.answer("Выберите курс обучения:", reply_markup=keyboard)
    await state.set_state(StudyNavigation.waiting_for_course)
    await callback.answer()

@dp.callback_query(F.data.startswith("course="), StudyNavigation.waiting_for_course)
async def course_selection_handler(callback: CallbackQuery, state: FSMContext):
    course_num = callback.data.split("=")[1]
    course = f"course_{course_num}"
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(text="1 семестр", callback_data=f"semester=1_course={course}")],
        [InlineKeyboardButton(text="2 семестр", callback_data=f"semester=2_course={course}")]])
    await callback.message.answer("Выберите семестр:", reply_markup=keyboard)
    await state.update_data(course=course)
    await state.set_state(StudyNavigation.waiting_for_semester)
    await callback.answer()

@dp.callback_query(F.data.startswith("semester="), StudyNavigation.waiting_for_semester)
async def semester_selection_handler(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    logging.info(f"Полученные данные: {data}")
    parts = data.split("_")
    if len(parts) < 2 or "course=" not in data:
        await callback.message.answer("❌ Ошибка в данных выбора семестра.")
        await callback.answer()
        return
    
    semester_part = parts[0]  # semester=1
    course_part = "_".join(parts[1:])  # course=course_1
    semester = semester_part.split("=")[1]
    course = course_part.split("=")[1]
    
    logging.info(f"Извлечено: course={course}, semester={semester}")
    if course and semester:
        semester_key = f"semester_{semester}"
        keyboard = create_disciplines_keyboard(course, semester_key)
        if keyboard:
            await callback.message.answer("Выберите дисциплину:", reply_markup=keyboard)
            await state.update_data(course=course, semester=semester_key)
            await state.set_state(StudyNavigation.waiting_for_discipline)
        else:
            await callback.message.answer("📚 Список дисциплин для данного курса и семестра пуст.")
    else:
        await callback.message.answer("❌ Ошибка при выборе курса или семестра.")
    await callback.answer()

@dp.callback_query(F.data.startswith("discipline_"), StudyNavigation.waiting_for_discipline)
async def discipline_selection_handler(callback: CallbackQuery, state: FSMContext):
    discipline_id = callback.data.split("_")[1]
    if discipline_id not in discipline_map:
        await callback.message.answer("❌ Ошибка: дисциплина не найдена.")
        await callback.answer()
        return
    course, semester, discipline = discipline_map[discipline_id]
    await show_recommended_literature(callback, course, semester, discipline)
    await state.finish()
    await callback.answer()

# 3️⃣ Поиск дисциплины
@dp.callback_query(F.data == "search_discipline")
@dp.message(F.text == "/search")
async def search_discipline_handler(message: Message, state: FSMContext):
    await message.answer("Введите название дисциплины для поиска:")
    await state.set_state(StudyNavigation.waiting_for_search_query)

@dp.message(StudyNavigation.waiting_for_search_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip().lower()
    results = []
    for course_key, course_data in disciplines_data.items():
        for semester_key, semester_data in course_data.items():
            for discipline, literature in semester_data.items():
                if query in discipline.lower():
                    results.append((course_key, semester_key, discipline, literature))
    
    if results:
        response_text = "🔍 Результаты поиска:\n\n"
        for course, semester, discipline, literature in results:
            response_text += f"📚 Дисциплина: <b>{discipline}</b> (Курс: {course.split('_')[1]}, Семестр: {semester.split('_')[1]})\n"
            if literature:
                for book in literature:
                    response_text += f"📖 <a href=\"{book['url']}\">{book['title']}</a>"
                    author_key = 'authors' if 'authors' in book else 'author'
                    if book.get(author_key):
                        response_text += f" ({book[author_key]})"
                    response_text += "\n"
            else:
                response_text += "Рекомендованная литература не найдена.\n"
            response_text += "\n"
        await message.answer(response_text, disable_web_page_preview=True)
    else:
        await message.answer(f"❌ Дисциплина с названием '{query}' не найдена.")
    await state.finish()

# ℹ️ Помощь
@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    help_text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "📘 <b>Рекомендуемая литература</b>: выберите курс и семестр, чтобы увидеть дисциплины.\n"
        "🔍 <b>Поиск дисциплины</b>: введите /search и название дисциплины.\n"
        "Ссылки ведут на IPR SMART (нужна авторизация)."
    )
    await callback.message.answer(help_text)
    await callback.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())