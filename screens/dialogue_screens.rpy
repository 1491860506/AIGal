
## Say screen ##################################################################
##
## The say screen is used to display dialogue to the player. It takes two
## parameters, who and what, which are the name of the speaking character and
## the text to be displayed, respectively. (The who parameter can be None if no
## name is given.)
##
## This screen must create a text displayable with id "what", as Ren'Py uses
## this to manage text display. It can also create displayables with id "who"
## and id "window" to apply style properties.
##
## https://www.renpy.org/doc/html/screen_special.html#say
# 新增 transform 动画定义
screen say(who, what):
    style_prefix "say"

    window:
        id "window"

        if who is not None:

            window:
                id "namebox"
                style "namebox"
                text who id "who"

        text what id "what"

    ## If there's a side image, display it in front of the text.
    add SideImage() xalign 0.0 yalign 1.0

## Make the namebox available for styling through the Character object.
init python:
    config.character_id_prefixes.append('namebox')

# Style for the dialogue window
style window:
    xalign 0.5
    yalign 1.0
    xysize (1231, 277)
    padding (40, 10, 40, 40)
    background Image("gui/textbox.png", xalign=0.5, yalign=1.0)

# Style for the dialogue
style say_dialogue:
    adjust_spacing False
    ypos 60
    # 你可以在这里为 text 本身设置一些基础样式 (虽然上面的 text displayable 会覆盖部分)
    # 例如:
    # properties { "line_spacing": 10 }

# The style for dialogue said by the narrator
style say_thought:
    is say_dialogue

# Style for the box containing the speaker's name
style namebox:
    xpos 20
    xysize (None, None)
    background Frame("gui/namebox.png", 5, 5, 5, 5, tile=False, xalign=0.0)
    padding (5, 5, 5, 5)

# Style for the text with the speaker's name
style say_label:
    color '#f93c3e'
    xalign 0.0
    yalign 0.5
    size gui.name_text_size
    font gui.name_text_font


## Quick Menu screen ###########################################################
##
## The quick menu is displayed in-game to provide easy access to the out-of-game
## menus.
## 按钮配色方案
define gui.button_default_image = "gui/button/button_default.png"
define gui.button_bg_fill_color = "#5e5e5e"
define gui.button_bg_stroke_color = "#ffffff"
define gui.button_bg_alpha = 0.45

define gui.button_default_stroke_color = "#ffffff"
define gui.button_yes_hover_color = "#ff6060"

define gui.button_no_hover_color = "#62f4bf"


define gui.button_auto_hover_color = "#ff9a77"
define gui.button_auto_selected_idle_color = "#ff7357"

define gui.button_load_hover_color = "#8295f6"

define gui.button_log_hover_color = "#d789ff"

define gui.button_save_hover_color = "#74e7e8"

define gui.button_skip_hover_color = "#ff77a4"

define gui.button_skip_selected_idle_color = "#ff5585"

define gui.button_system_hover_color = "#ff98ea"

define gui.button_return_hover_color = "637bee"

define gui.button_title_hover_color = "95bf64"

define gui.button_exit_hover_color = "f92a2a"
transform button_fadeinout:
    alpha 0.0
    on hover:
        linear 0.5 alpha 1.0

    on idle:
        linear 0.5 alpha 0.0
transform screenfadeinout(st = 0.5):
    alpha 0.0
    on show:
        linear st alpha 1.0
    on hide:
        linear st alpha 0.0




screen quick_menu_show_area():
    zorder 101
    
    mousearea:
        area (0, 1040, 1920, 40)
        hovered Show("quick_menu")
        unhovered Hide("quick_menu")


transform quick_button_base_fade:
    alpha 0.0
    on show:
        linear 0.5 alpha 1.0
    on hide:
        linear 0.5 alpha 0.0

transform quick_menu_buttons_transform:
    yoffset 0
    on show:
        linear 0.5 yoffset 0
    on hide:
        linear 0.5 yoffset 0

default quick_menu = True

screen quick_menu():

    zorder 100

    if quick_menu:

        # 使用 frame 作为 hbox 的背景
        frame:
            style "quick_frame" # 应用 frame 的样式
            at quick_button_base_fade
            hbox:
                style "quick_hbox" # hbox 样式保持，或者微调
                button:
                    if (config.allow_skipping == True):
                        background im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    else:
                        background im.MatrixColor(gui.button_default_image, im.matrix.colorize("#000", "#000"), xalign=0.5, yalign = 0.5)
                    if (renpy.is_skipping() == True):
                        add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_skip_selected_idle_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5)
                    else:
                        add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_skip_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("跳过", xalign=0.5, yalign = 0.5, size = 25)
                    action Skip() alternate Skip(fast=True, confirm=True)
                # autoplay
                button:
                    background im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    if (preferences.afm_enable == True):
                        add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_auto_selected_idle_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5)
                    else:
                        add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_auto_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("自动", xalign=0.5, yalign = 0.5, size = 25)
                    action Preference("auto-forward", "toggle")
                # save
                button:
                    background im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_save_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("存档", xalign=0.5, yalign = 0.5, size = 25)
                    action ShowMenu("save")
                # load
                button:
                    background im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_load_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("读档", xalign=0.5, yalign = 0.5, size = 25)
                    action ShowMenu("load")
                button:
                    background im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_log_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("历史", xalign=0.5, yalign = 0.5, size = 25)
                    action ShowMenu("history")
                button:
                    background im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    add im.MatrixColor(gui.button_default_image, im.matrix.colorize(gui.button_system_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("设置", xalign=0.5, yalign = 0.5, size = 25)
                    action ShowMenu("preferences")
                at quick_menu_buttons_transform

init python:
    #config.overlay_screens.append("quick_menu")
    config.overlay_screens.append("quick_menu_show_area")


# 样式定义
style quick_frame:
    # 示例：半透明黑色背景，圆角 (需要对应 frame 图片)
    #background Frame("gui/frame.png", 10, 10) # 使用可伸缩的 frame 图片
    background "#ffffff00" # 或者简单的半透明黑色
    xalign 0.5
    yalign 1.0
    yoffset -8 # 调整整体位置
    padding (0, 0) # 内部边距

style quick_hbox:
    xalign 0.5 # 在 frame 内部居中
    # yalign 0.5 # 如果 frame 有固定高度，可以垂直居中 hbox
    spacing 20 # 增大按钮间距






## NVL screen ##################################################################
##
## This screen is used for NVL-mode dialogue and menus.
##
## https://www.renpy.org/doc/html/screen_special.html#nvl


screen nvl(dialogue, items=None):

    window:
        style "nvl_window"

        has vbox
        spacing 15

        use nvl_dialogue(dialogue)

        ## Displays the menu, if given. The menu may be displayed incorrectly if
        ## config.narrator_menu is set to True.
        for i in items:

            textbutton i.caption:
                action i.action
                style "nvl_button"

    add SideImage() xalign 0.0 yalign 1.0


screen nvl_dialogue(dialogue):

    for d in dialogue:

        window:
            id d.window_id

            fixed:
                yfit True

                if d.who is not None:

                    text d.who:
                        id d.who_id

                text d.what:
                    id d.what_id


## This controls the maximum number of NVL-mode entries that can be displayed at
## once.
define config.nvl_list_length = 6

# The style for the NVL "textbox"
style nvl_window:
    is default
    xfill True yfill True
    background "gui/nvl.png"
    padding (0, 15, 0, 30)

# The style for the text of the speaker's name
style nvl_label:
    is say_label
    xpos 645 xanchor 1.0
    ypos 0 yanchor 0.0
    xsize 225
    min_width 225
    textalign 1.0

# The style for dialogue in NVL
style nvl_dialogue:
    is say_dialogue
    xpos 675
    ypos 12
    xsize 885
    min_width 885

# The style for dialogue said by the narrator in NVL
style nvl_thought:
    is nvl_dialogue

style nvl_button:
    xpos 675
    xanchor 0.0


## Bubble screen ###############################################################
##
## The bubble screen is used to display dialogue to the player when using speech
## bubbles. The bubble screen takes the same parameters as the say screen, must
## create a displayable with the id of "what", and can create displayables with
## the "namebox", "who", and "window" ids.
##
## https://www.renpy.org/doc/html/bubble.html#bubble-screen

screen bubble(who, what):
    style_prefix "bubble"

    window:
        id "window"

        if who is not None:

            window:
                id "namebox"
                style "bubble_namebox"

                text who:
                    id "who"

        text what:
            id "what"

style bubble_window:
    is empty
    xpadding 30
    top_padding 5
    bottom_padding 5

style bubble_namebox:
    is empty
    xalign 0.5

style bubble_who:
    is default
    xalign 0.5
    textalign 0.5
    color "#000"

style bubble_what:
    is default
    align (0.5, 0.5)
    text_align 0.5
    layout "subtitle"
    color "#000"

define bubble.frame = Frame("gui/bubble.png", 55, 55, 55, 95)
define bubble.thoughtframe = Frame("gui/thoughtbubble.png", 55, 55, 55, 55)

define bubble.properties = {
    "bottom_left" : {
        "window_background" : Transform(bubble.frame, xzoom=1, yzoom=1),
        "window_bottom_padding" : 27,
    },

    "bottom_right" : {
        "window_background" : Transform(bubble.frame, xzoom=-1, yzoom=1),
        "window_bottom_padding" : 27,
    },

    "top_left" : {
        "window_background" : Transform(bubble.frame, xzoom=1, yzoom=-1),
        "window_top_padding" : 27,
    },

    "top_right" : {
        "window_background" : Transform(bubble.frame, xzoom=-1, yzoom=-1),
        "window_top_padding" : 27,
    },

    "thought" : {
        "window_background" : bubble.thoughtframe,
    }
}

define bubble.expand_area = {
    "bottom_left" : (0, 0, 0, 22),
    "bottom_right" : (0, 0, 0, 22),
    "top_left" : (0, 22, 0, 0),
    "top_right" : (0, 22, 0, 0),
    "thought" : (0, 0, 0, 0),
}
