# Weather Route Bot

Телеграм-бот для получения прогноза погоды по маршруту путешествия.

## Возможности
- Прогноз погоды для нескольких городов
- Визуализация маршрута на карте
- График изменения температуры
- Детальный прогноз по часам

## Установка
1. Клонируйте репозиторий
2. Установите зависимости: `pip install -r requirements.txt`
3. Создайте файл `.env` с токеном бота и ключом API openweather (Я использовал API openweather, а не API accuweather, потому что использовал его в прошлом проекте, он показался мне более удобным (намного больше вызовов)
4. Запустите бота: `python bot.py`

## Использование
1. Отправьте `/start` для начала работы
2. Используйте `/weather` для получения прогноза
3. Введите города через запятую
4. Выберите количество дней
5. Получите прогноз и визуализации

## Команды
- `/start` - Начать работу с ботом
- `/weather` - Получить прогноз погоды
- `/help` - Показать справку

## Примеры использоования:

![image](https://github.com/user-attachments/assets/05942cb0-dadf-4fd2-af2d-f8d57cff31ca)

![image](https://github.com/user-attachments/assets/b710a766-9fb6-4f35-a621-10b2c6107935)

Можно загружать много городов. Найдите пасхалку в графике. Ответ в конце файла.

![image](https://github.com/user-attachments/assets/777159f0-6332-40d0-bdea-f15d85d301b8)

Пасхалка в том, что города в легенде выстроены в порядке правил игры в города (буква конца слова Москва = буква начала слова Архангельск)
