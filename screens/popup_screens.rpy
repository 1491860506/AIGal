
## Confirm screen ##############################################################
##
## The confirm screen is called when Ren'Py wants to ask the player a yes or no
## question.
##
## https://www.renpy.org/doc/html/screen_special.html#confirm

screen confirm(message, yes_action, no_action):

    ## 显示此界面时，确保其他界面无法输入。
    modal True

    zorder 200

    style_prefix "confirm"

    add "gui/overlay/confirm.png" at screenfadeinout(0.5)

    frame:

        at screenfadeinout(0.5)
        vbox:
            xalign .5
            yalign .5
            spacing 30

            label _(message):
                style "confirm_prompt"
                xalign 0.5

            hbox:
                xalign 0.5
                spacing 100

                # textbutton _("确定") action yes_action
                # textbutton _("取消") action no_action
                button:
                    xoffset 50
                    background im.MatrixColor("gui/button/button_default.png", im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    add im.MatrixColor("gui/button/button_default.png", im.matrix.colorize(gui.button_yes_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("YES", xalign=0.5, yalign = 0.5, size = 25)
                    action yes_action

                button:
                    xoffset -50
                    background im.MatrixColor("gui/button/button_default.png", im.matrix.colorize(gui.button_bg_fill_color, gui.button_bg_stroke_color) * im.matrix.opacity(gui.button_bg_alpha), xalign=0.5, yalign = 0.5)
                    add im.MatrixColor("gui/button/button_default.png", im.matrix.colorize(gui.button_no_hover_color, gui.button_default_stroke_color), xalign=0.5, yalign = 0.5) at button_fadeinout
                    foreground Text("NO", xalign=0.5, yalign = 0.5, size = 25)
                    action no_action

    ## 右键点击退出并答复“no”（取消）。
    key "game_menu" action no_action



define gui.confirm_frame_borders = Borders(40, 40, 40, 40)
define gui.frame_tile = False
define gui.button_tile = False
define gui.button_borders = Borders(4, 4, 4, 4)
style confirm_frame is gui_frame
style confirm_prompt is gui_prompt
style confirm_prompt_text is gui_prompt_text
style confirm_button is gui_medium_button
style confirm_button_text is gui_medium_button_text

style confirm_frame:
    background Frame([ "gui/confirm_frame.png", "gui/frame.png"], gui.confirm_frame_borders, tile=gui.frame_tile)
    padding gui.confirm_frame_borders.padding
    xalign .5
    yalign .5

style confirm_prompt_text:
    text_align 0.5
    layout "subtitle"
    size 35
    color '#000000'

style confirm_button:
    properties gui.button_properties("confirm_button")

style confirm_button_text:
    properties gui.button_text_properties("confirm_button")


## Skip indicator screen #######################################################
##
## The skip_indicator screen is displayed to indicate that skipping is in
## progress.
##
## https://www.renpy.org/doc/html/screen_special.html#skip-indicator

screen skip_indicator():

    zorder 100
    style_prefix "skip"

    frame:
        has hbox

        text _("Skipping")

        text "▸" at delayed_blink(0.0, 1.0) style "skip_triangle"
        text "▸" at delayed_blink(0.2, 1.0) style "skip_triangle"
        text "▸" at delayed_blink(0.4, 1.0) style "skip_triangle"


## This transform is used to blink the arrows one after another.
transform delayed_blink(delay, cycle):
    alpha .5

    pause delay

    block:
        linear .2 alpha 1.0
        pause .2
        linear .2 alpha 0.5
        pause (cycle - .4)
        repeat

style skip_hbox:
    spacing 9

style skip_frame:
    is empty
    ypos 15
    background Frame("gui/skip.png", 24, 8, 75, 8, tile=False)
    padding (24, 8, 75, 8)

style skip_text:
    size 24

style skip_triangle:
    is skip_text
    ## We have to use a font that has the BLACK RIGHT-POINTING SMALL TRIANGLE
    ## glyph in it.
    font "DejaVuSans.ttf"

## Notify screen ###############################################################
##
## The notify screen is used to show the player a message. (For example, when
## the game is quicksaved or a screenshot has been taken.)
##
## https://www.renpy.org/doc/html/screen_special.html#notify-screen

screen notify(message):

    zorder 100
    style_prefix "notify"

    frame at notify_appear:
        text "[message!tq]"

    timer 3.25 action Hide('notify')


transform notify_appear:
    on show:
        alpha 0
        linear .25 alpha 1.0
    on hide:
        linear .5 alpha 0.0


style notify_frame:
    is empty
    ypos 68

    background Frame("gui/notify.png", 24, 8, 60, 8, tile=False)
    padding (24, 8, 60, 8)

style notify_text:
    size 24



