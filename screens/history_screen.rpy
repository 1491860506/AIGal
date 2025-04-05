
## History screen ##############################################################
##
## This is a screen that displays the dialogue history to the player. While
## there isn't anything special about this screen, it does have to access the
## dialogue history stored in _history_list.
##
## https://www.renpy.org/doc/html/history.html

define config.history_length = 250


transform scale_to_height(target_height):
    ysize target_height
    fit "contain"


screen history():
    tag menu

    add "gui/history/bg.png"
    add "gui/history/title.png":
        pos (730, 30)
        xysize (459, 136)

    ## 避免预缓存此界面，因为它可能非常大。
    predict False

    frame:
        background None
        align (0.5, 0.5)
        xysize (1450, 700)

        has vpgrid
        
        id "vp"
        cols 1
        yinitial 1.0
        spacing 40

        mousewheel True
        draggable True
        xalign 0.5

        for h in _history_list:
            window:
                background None
                xysize (1400, 220)
                xalign 0.5

                has fixed:
                    yfit True

                frame:
                    xalign 0.5
                    yoffset 40

                    background "gui/history/frame.png"
                    xysize (840, 162)

                    $ what = renpy.filter_text_tags(h.what, allow=gui.history_allow_tags)
                    frame:
                        background None
                        align (0.5, 0.5)
                        text what:
                            substitute False
                            xsize 550
                            align (0.0, 0.5)
                            color "#000"
                    frame:
                        button:
                            style "base_button"
                            hover_background "gui/button/back_hover.png"
                            background "gui/button/back.png"
                            xysize (50,50)
                            pos (750,-10)
                            action Confirm("是否跳转到对应对话",RollbackToIdentifier(h.rollback_identifier),None)
                            

                if h.who:
                    frame:
                        background "gui/history/name.png"
                        xysize (194, 74)
                        pos (200, 0)
                        text _(h.who):
                            xalign 0.5
                            yalign 0.5
                            color "#68535a"
                            size 33
                            xsize 185
                if os.path.exists(os.path.join(game_directory, "data", title, "images", f"{h.who}.png")):
                    frame:
                        background None
                        xysize (151, 151)
                        pos (0, 0)

                        $ history_icon = os.path.join(game_directory, "data", title, "images", f"{h.who}.png").replace('\\','/')
                        image history_icon at scale_to_height(200)
                if h.voice.filename:
                    frame:
                        button:
                            style "base_button"
                            hover_background "gui/button/voice_hover.png"
                            background "gui/button/voice.png"
                            xysize (50,50)
                            pos (930,40)
                            action Play("voice",h.voice.filename)
    button:
        background "gui/history/return.png"
        hover_background "gui/history/return_hover.png"
        style "base_button"
        text _("返回"):
            size 50
            color "#fff"
            hover_color "#d37b93"
            align (0.5, 0.5)

        xysize (232, 101)
        align (1.0, 0.95)
        action Return()

    vbar value YScrollValue("vp"):
        pos (1500, 200)
        xysize (30, 700)
        top_bar Solid("#00f0")
        bottom_bar Solid("#00f0")
        thumb "gui/history/bar.png"


define gui.history_allow_tags = { "alt", "noalt", "rt", "rb", "art" }
## 历史屏幕条目的高度，或设置为 None 以使高度变量自适应。
define gui.history_height = 210

style history_window:
    xfill True
    ysize gui.history_height

