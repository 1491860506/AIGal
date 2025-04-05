## Load and Save screens #######################################################
##
## These screens are responsible for letting the player save the game and load
## it again. Since they share nearly everything in common, both are implemented
## in terms of a third screen, file_slots.
##
## https://www.renpy.org/doc/html/screen_special.html#save
## https://www.renpy.org/doc/html/screen_special.html#load


## The width and height of thumbnails used by the save slots.
define config.thumbnail_width = 400
define config.thumbnail_height = 225


define gui.slot_button_width = 780
## 按钮高度
define gui.slot_button_height = 243
define gui.slot_button_borders = Borders(15, 15, 15, 15)
## 按钮字大小
define gui.slot_button_text_size = 30
## 按钮字居中
define gui.slot_button_text_xalign = 0.5
 

## 存档网格中的列数和行数。
define gui.file_slot_cols = 3
define gui.file_slot_rows = 2

define gui.slot_spacing=15



define gui.hover_color = '#66c1e0'
screen save():

    tag menu

    use file_slots(_("Save"))


screen load():

    tag menu

    use file_slots(_("Load"))


screen file_slots(title):
    add "gui/save/bg.png"
    default page_name_value = FilePageNameInputValue(pattern=_("第 {} 页"), auto=_("自动存档"), quick=_("快速存档"))

    add "gui/save/{:s}.png".format(title):
        if title == "save":
            xysize (356, 196)
        elif title == "load":
            xysize (365, 203)
        pos (150, 120)

    fixed:

        ## 此代码确保输入控件在任意按钮执行前可以获取 enter 事件。
        order_reverse True

        ## 页面名称，可以通过单击按钮进行编辑。
        button:
            style "page_label"

            key_events True
            xalign 0.5
            #action page_name_value.Toggle()

            input:
                style "page_label_text"
                value page_name_value



        ## 存档位网格。
        grid gui.file_slot_cols gui.file_slot_rows:
            style_prefix "slot"

            yalign 0.5
            xpos 600

            spacing gui.slot_spacing

            for i in range(gui.file_slot_cols * gui.file_slot_rows):

                $ slot = i + 1

                button:
                    xalign 0.5
                    xysize (382, 302)
                    action FileAction(slot)
                    has vbox
                    add FileScreenshot(slot):
                        xalign 0.5
                        xysize (340, 191)
                    text FileTime(slot, format=_("{#file_time}%Y-%m-%d %H:%M"), empty=_("空存档位")):
                        style "slot_time_text"
                        color "#68535a"
                        yoffset 10
                    if FileTime(slot):  # 检测是否有存档
                        textbutton "删除存档":
                            style "slot_time_text"
                            text_color "#68535a"
                            hover_background "#eddf48"
                            yoffset 20
                            action FileDelete(slot)
        ## 用于访问其他页面的按钮。
        hbox:
            style_prefix "page"

            pos (470, 920)
            if start_page>=10:
                spacing 50
            else:
                if config.has_autosave and config.has_quicksave:
                    spacing 78
                elif config.has_autosave or config.has_quicksave:
                    spacing 81
                else:
                    spacing 84
            #spacing gui.page_spacing


            textbutton _("<") action Function(previous_page_range)

            if config.has_autosave:
                textbutton _("{#auto_page}A") action FilePage("auto")

            if config.has_quicksave:
                textbutton _("{#quick_page}Q") action FilePage("quick")

            ## 显示当前页面范围中的页码
            for page in range(start_page, end_page + 1):
                textbutton "[page]" action FilePage(page)

            textbutton _(">") action Function(next_page_range)

    vbox:
        spacing 5
        pos (80, 600)

        style_prefix "file_slots"
        button:
            text _("返回"):
                style "file_slots_button_text"
            action Return()

        button:
            text _("主界面"):
                style "file_slots_button_text"
            if main_menu:
                action Return()
            else:
                action MainMenu()


init python:
    # 初始化页面范围
    start_page = 1
    end_page = 9

    def previous_page_range():
        global start_page, end_page
        if start_page > 1:
            start_page -= 9
            end_page -= 9

    def next_page_range():
        global start_page, end_page
        if end_page < 99:
            start_page += 9
            end_page += 9

style page_button is gui_button
style page_button_text is gui_button_text

style slot_button is gui_button
style slot_button_text is gui_button_text
style slot_time_text is slot_button_text
style slot_name_text is slot_button_text


style file_slots_button is base_button:
    background "gui/save/button.png"
    hover_background "gui/save/button_hover.png"
    xysize (274, 99)

style file_slots_button_text:
    align (0.5, 0.5)
    size 40
    hover_color "#5fc6c8"
    color "#fff"

style page_label:
    xpadding 75
    ypadding 5

style page_label_text:
    pos (140 ,70)
    layout "subtitle"
    hover_color gui.hover_color
    size 57
    color "#e37595"


style page_button_text:
    properties gui.button_text_properties("page_button")
    color "#e37595"
    hover_color "#bdfb05"
    selected_color "#0b94ee"
    size 57
    bold True

style slot_button:
    properties gui.button_properties("slot_button")

style slot_button_text:
    properties gui.button_text_properties("slot_button")
