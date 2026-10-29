"""Браузерные сценарии. Требуются Python Playwright и Chromium; сервер: npm start."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('EGO_URL', 'http://127.0.0.1:3000')
ARTIFACTS = Path(os.environ.get('EGO_ARTIFACTS', '/tmp/ego-tests'))
ARTIFACTS.mkdir(parents=True, exist_ok=True)

def route(page, name):
    page.goto(BASE + '/#' + name)
    page.wait_for_selector('#main')

def local(page):
    return page.evaluate("JSON.parse(localStorage.getItem('ego:v1'))")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True, args=['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
        context = browser.new_context(viewport={'width':1440,'height':1000}, permissions=['microphone'], accept_downloads=True)
        page = context.new_page()
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        route(page, 'home')
        expect(page.locator('h1')).to_contain_text('Сегодня')
        page.screenshot(path=str(ARTIFACTS / 'desktop.png'), full_page=True)
        print('PASS: главная и запуск приложения')
        route(page, 'lesson/intro')
        expect(page.locator('.reading-section')).to_have_count(5)
        page.locator('#topic-note').fill('Философия начинается с вопроса.')
        page.locator('#note-tags').fill('вопросы, знание')
        page.locator('#open-answer').fill('Обещания создают ожидания. Но предотвращение вреда может быть важнее.')
        page.get_by_role('button', name='Сохранить тему', exact=True).click()
        page.get_by_role('button', name='Отметить как изученную').click()
        page.reload()
        expect(page.locator('#topic-note')).to_have_value('Философия начинается с вопроса.')
        expect(page.locator('#open-answer')).to_have_value('Обещания создают ожидания. Но предотвращение вреда может быть важнее.')
        assert local(page)['completed']==['intro']
        route(page,'topics')
        page.get_by_role('button',name='Сохранённые',exact=True).click()
        expect(page.locator('.topic-card')).to_have_count(1)
        print('PASS: чтение, заметки, теги, открытый ответ, закладки и прогресс после перезагрузки')
        route(page,'quiz/intro')
        # Первую ошибку исправляем через отдельный повтор ошибок.
        choices=[0,2,0,1,0,2]
        for i,j in enumerate(choices):
            page.locator(f'[data-action="answer"][data-index="{i}"][data-choice="{j}"]').click()
        expect(page.locator('.explanation')).to_have_count(6)
        expect(page.locator('.result-card h2')).to_have_text('5 из 6')
        page.get_by_role('button',name='Повторить ошибки').click()
        expect(page.locator('.question-card')).to_have_count(1)
        page.locator('[data-action="answer"][data-choice="1"]').click()
        expect(page.locator('.result-card h2')).to_have_text('1 из 1')
        page.reload()
        assert local(page)['quiz']['intro']['score']==1
        print('PASS: тест, объяснения, результат и повтор ошибок')
        route(page,'essay/stoic/1')
        text='Счастье связано с выбором, но внешние условия тоже важны. Например, болезнь ограничивает возможности человека.'
        page.locator('#essay-text').fill(text)
        page.get_by_role('button',name='Показать подсказки').click()
        expect(page.locator('#essay-text')).to_have_value(text)
        page.reload()
        expect(page.locator('#essay-text')).to_have_value(text)
        expect(page.locator('[data-count]')).to_contain_text('слов')
        print('PASS: эссе, подсказки, счётчик и автосохранение')
        route(page,'library')
        page.locator('[data-book-status="oldman"]').select_option('reading')
        page.locator('#library-status').select_option('reading')
        expect(page.locator('.library-card')).to_have_count(1)
        page.get_by_role('button',name='Подробнее о книге Старик и море').click()
        expect(page.locator('#modal')).to_be_visible()
        expect(page.locator('#modal-content')).to_contain_text('не утверждение о прямом влиянии')
        page.get_by_role('button',name='Закрыть',exact=True).click()
        page.reload()
        assert local(page)['bookStatus']['oldman']=='reading'
        print('PASS: библиотека, фильтр, рекомендации и сохранение статуса')
        route(page,'practice/speech')
        page.clock.install()
        page.locator('#speech-scope').select_option('learned')
        page.get_by_role('button',name='Получить вопрос').click()
        expect(page.locator('.speech-question')).to_contain_text('Что такое философия')
        expect(page.locator('#timer-value')).to_have_text('05:00')
        page.locator('#speech-notes').fill('Тезис: сомнение помогает проверять основания.')
        page.clock.fast_forward(300000)
        expect(page.locator('#timer-label')).to_have_text('Выступление')
        page.clock.fast_forward(65000)
        expect(page.locator('#timer-value')).to_have_text('01:05')
        page.get_by_role('button',name='Завершить выступление').click()
        expect(page.locator('#timer-label')).to_have_text('Практика завершена')
        page.locator('[data-speech-check="0"]').check()
        page.get_by_role('button',name='Сохранить практику').click()
        assert local(page)['speeches'][0]['checks']==[0]
        assert local(page)['speeches'][0]['elapsed']==65
        page.get_by_role('button',name='Другой вопрос').click()
        page.get_by_role('button',name='Начать выступление',exact=True).click()
        expect(page.locator('#timer-label')).to_have_text('Выступление')
        print('PASS: изученные темы, случайный вопрос, 5 минут подготовки, ранний старт, таймер речи и самооценка')
        page.clock.resume()
        page.get_by_role('button',name='Записать голос',exact=True).click()
        expect(page.get_by_role('button',name='Остановить запись')).to_be_visible()
        page.wait_for_timeout(1300)
        page.get_by_role('button',name='Остановить запись').click()
        expect(page.locator('#audio-preview audio')).to_be_visible()
        audio_size=page.evaluate("async()=>{const a=document.querySelector('audio'); const b=await (await fetch(a.src)).blob(); return b.size}")
        assert audio_size>100
        page.get_by_role('button',name='Завершить выступление').click()
        page.wait_for_function("JSON.parse(localStorage.getItem('ego:v1')).speeches.some(x=>x.audio)")
        page.reload()
        expect(page.locator('#timer-label')).to_have_text('Практика завершена')
        page.locator('#speech-notes').fill('Обновлённые тезисы после перезагрузки')
        page.get_by_role('button',name='Сохранить практику').click()
        page.wait_for_function("JSON.parse(localStorage.getItem('ego:v1')).speeches.some(x=>x.audio && x.text.includes('Обновлённые'))")
        route(page,'notes')
        page.get_by_role('button',name='Прослушать',exact=False).first.click()
        expect(page.locator('#modal audio')).to_be_visible()
        with page.expect_download() as dl:
            page.get_by_role('button',name='Скачать аудио').click()
        assert Path(dl.value.path()).stat().st_size>100
        page.get_by_role('button',name='Удалить аудио').click()
        expect(page.locator('#modal')).not_to_be_visible()
        assert not any(x['audio'] for x in local(page)['speeches'])
        print('PASS: запись с виртуальным микрофоном, Blob, IndexedDB, воспроизведение, скачивание и удаление аудио')
        page.locator('#notes-search').fill('знание')
        expect(page.locator('.note-card')).to_have_count(1)
        page.locator('#notes-search').fill('несуществующийтекст')
        expect(page.locator('.empty')).to_contain_text('Ничего не найдено')
        page.locator('#notes-search').fill('')
        page.locator('#notes-filter').select_option('essay')
        expect(page.locator('.note-card')).to_have_count(1)
        with page.expect_download() as dl:
            page.get_by_role('button',name='Экспортировать',exact=True).click()
        assert 'Счастье связано с выбором' in Path(dl.value.path()).read_text()
        print('PASS: поиск по тегам, фильтры и содержательный экспорт')
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        for dest in ['home','topics','lesson/stoic','quiz/exist','essay/intro/0','practice','practice/speech','library','notes']:
            route(m,dest)
            assert m.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Горизонтальное переполнение: '+dest
            expect(m.locator('.sidebar')).to_be_visible()
        route(m,'home')
        m.screenshot(path=str(ARTIFACTS / 'mobile.png'),full_page=True)
        print('PASS: девять экранов на ширине 390px без горизонтального переполнения')
        denied=browser.new_context(viewport={'width':1100,'height':800})
        d=denied.new_page()
        # Детерминированный отказ в разрешении, без виртуального разрешения запуска браузера.
        d.add_init_script("Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async()=>{throw new DOMException('Denied','NotAllowedError')}})")
        route(d,'practice/speech')
        d.get_by_role('button',name='Получить вопрос').click()
        d.get_by_role('button',name='Записать голос',exact=True).click()
        expect(d.locator('#toast')).to_contain_text('не разрешён')
        d.locator('#speech-notes').fill('Можно продолжить без микрофона')
        d.get_by_role('button',name='Начать выступление',exact=True).click()
        d.get_by_role('button',name='Завершить выступление').click()
        assert local(d)['speeches'][0]['text']=='Можно продолжить без микрофона'
        print('PASS: отказ в микрофоне не блокирует таймер, тезисы и сохранение')
        assert not errors, errors
        print('PASS: нет необработанных ошибок JavaScript')
        browser.close()

if __name__=='__main__':
    run()
