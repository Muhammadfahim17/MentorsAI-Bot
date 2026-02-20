from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_name = State()
    waiting_surname = State()
    waiting_age = State()
    waiting_role = State()
    waiting_photo = State()

class Menu(StatesGroup):
    main = State()

class Learning(StatesGroup):
    choosing_category = State()
    choosing_subcategory = State()
    viewing_material = State()
    taking_test = State()
    rating_course = State()

class AdminPanel(StatesGroup):
    main = State()
    add_category = State()
    add_subcategory = State()
    choose_category_for_sub = State()
    add_material = State()
    choose_category_for_material = State()
    choose_subcategory_for_material = State()
    material_name = State()
    material_desc = State()
    material_content = State()
    add_sponsor = State()
    delete_sponsor = State()
    delete_category = State()
    delete_subcategory = State()
    delete_material = State()
    broadcast_name = State()
    broadcast_desc = State()
    broadcast_content = State()
    broadcast_button_text = State()
    broadcast_button_url = State()