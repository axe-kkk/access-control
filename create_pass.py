from PIL import Image, ImageDraw, ImageFont
import os

def mm_to_pixels(mm):
    return int(mm * 300 / 25.4)


def create(number, f_name, m_name, l_name, date1, date2, car_number1, storages):
    # Размеры изображения в миллиметрах и их конвертация в пиксели
    width_mm = 204
    height_mm = 70
    width = mm_to_pixels(width_mm)
    height = mm_to_pixels(height_mm)

    # Создание нового белого изображения
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Толщина границы и линий в миллиметрах и их конвертация в пиксели
    border_thickness_mm = 0.5
    border_thickness = mm_to_pixels(border_thickness_mm)

    # Рисование границы вокруг изображения
    draw.rectangle([0, 0, width, height], outline="black", width=border_thickness)

    # Рисование вертикальной линии посередине изображения
    draw.line([width // 2 - mm_to_pixels(0.5), 0, width // 2 - mm_to_pixels(0.5), height], fill="black",
              width=border_thickness)

    # Рисование горизонтальной линии (часть квадратов)
    draw.line([0, height - mm_to_pixels(17), width, height - mm_to_pixels(17)], fill="black", width=border_thickness)

    draw.line([width // 2 + mm_to_pixels(7), mm_to_pixels(25), width - mm_to_pixels(7), mm_to_pixels(25)], fill="black",
              width=border_thickness)
    draw.line([width // 2 + mm_to_pixels(7), mm_to_pixels(40), width - mm_to_pixels(7), mm_to_pixels(40)], fill="black",
              width=border_thickness)

    # Рисование вертикальных линий для создания квадратов
    for i in range(1, 12):
        draw.line([mm_to_pixels(17) * i, height - mm_to_pixels(17), mm_to_pixels(17) * i, height], fill="black",
                  width=border_thickness)

    # Задание шрифта и размера текста
    font = ImageFont.truetype("arial.ttf", 36)

    # Задание текста и его позиции
    text = "Пропуск № "
    text_position = (mm_to_pixels(35), mm_to_pixels(5))
    draw.text(text_position, text, fill="black", font=font)

    zero = (6 - len(number)) * '0'
    number = zero + number
    text_position = (mm_to_pixels(55), mm_to_pixels(5))
    draw.text(text_position, number, fill="black", font=font)

    text_position = (mm_to_pixels(35), mm_to_pixels(13))
    draw.text(text_position, f_name, fill="black", font=font)

    text_position = (mm_to_pixels(35), mm_to_pixels(21))
    draw.text(text_position, m_name, fill="black", font=font)

    text_position = (mm_to_pixels(35), mm_to_pixels(29))
    draw.text(text_position, l_name, fill="black", font=font)

    date = "Действительный"
    text_position = (mm_to_pixels(35), mm_to_pixels(40))
    draw.text(text_position, date, fill="black", font=font)

    text_position = (mm_to_pixels(65), mm_to_pixels(36))
    draw.text(text_position, date1, fill="black", font=font)

    text_position = (mm_to_pixels(65), mm_to_pixels(44))
    draw.text(text_position, date2, fill="black", font=font)

    car_number = "Авто"
    text_position = (mm_to_pixels(5), mm_to_pixels(47))
    draw.text(text_position, car_number, fill="black", font=font)

    text_position = (mm_to_pixels(15), mm_to_pixels(47))
    draw.text(text_position, car_number1, fill="black", font=font)

    text2 = "Передача пропуска другим лицам"
    text_position = (width // 2 + mm_to_pixels(30 - 2), mm_to_pixels(5))
    draw.text(text_position, text2, fill="black", font=font)

    text3 = "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНА"
    text_position = (width // 2 + mm_to_pixels(31 - 2), mm_to_pixels(10))
    draw.text(text_position, text3, fill="black", font=font)

    text3 = "подпись арендатора"
    text_position = (width // 2 + mm_to_pixels(36), mm_to_pixels(26))
    draw.text(text_position, text3, fill="black", font=font)

    text3 = "подпись администрации"
    text_position = (width // 2 + mm_to_pixels(35), mm_to_pixels(40))
    draw.text(text_position, text3, fill="black", font=font)

    for i in range(len(storages)):
        text = storages[i].split('/')
        for j in range(len(text)):
            text_position = (mm_to_pixels(2 + 17*i),  mm_to_pixels(54 + 4*j))
            draw.text(text_position, text[j], fill="black", font=font)

    font = ImageFont.truetype("arial.ttf", 52)
    for i in range(6):
        text_position = (width // 2 + mm_to_pixels(7 + 17*i),  mm_to_pixels(59))
        draw.text(text_position, number[i], fill="black", font=font)
    # Сохранение изображения
    #image_path = "static/img/Pass.png"
    #image.save(image_path)
    return image


def create_pass(number, f_name, m_name, l_name, date1, date2, car_number1, storages):
    a4_width_mm = 210
    a4_height_mm = 297
    a4_width = mm_to_pixels(a4_width_mm)
    a4_height = mm_to_pixels(a4_height_mm)
    a4_image = Image.new("RGB", (a4_width, a4_height), "white")
    pass_image = create(number, m_name, f_name, l_name, date1, date2, car_number1, storages)
    offset = (mm_to_pixels(1.5), mm_to_pixels(1))
    a4_image.paste(pass_image, offset)
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)))
    a4_image_path = path + "/static/img/Pass.png"
    a4_image.save(a4_image_path)


