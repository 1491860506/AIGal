
## Preferences screen ##########################################################
##
## The preferences screen allows the player to configure the game to better suit
## themselves.
##
## https://www.renpy.org/doc/html/screen_special.html#preferences

screen preferences():
    zorder 10
    modal True
    tag menu
    dismiss action Return()
    add "gui/setting/bg.png"
    add "gui/setting/setting_font.png":
        pos (730, 40)
        xysize (439,148)


    frame:
        background "gui/volume/frame.png"
        xysize (1379,766)
        pos (300, 157)

        has vbox
        style_prefix "volume"
        align (0.5, 0.3)
        spacing 5

        text _("音乐音量")

        hbox:
            bar:
                value Preference("music volume")
                style "volume_bar"
        null height 10
        text _("音效音量")

        hbox:
            bar:
                value Preference("sound volume")
                style "volume_bar"
        
        null height 10

        text _("语音音量")

        hbox:
            bar:
                value Preference("voice volume")
                style "volume_bar"
        null height 10

        text _("文本显示速度")

        hbox:
            bar:
                value Preference("text speed")
                style "volume_bar"
        null height 10

        text _("自动播放间隔")

        hbox:
            bar:
                value Preference("auto-forward time")
                style "volume_bar"

    frame:
        xysize (600,400)
        pos (320, 380)
        style_prefix "radio"
        has vbox
        align (0.5, 0.3)
        spacing 5
        label _("音量调节")
        null height 120
        label _("速度调节")
        null height 100
        label _("窗口调节")
        null height 20
    frame:
        xysize (600,400)
        pos (660,600)
        has hbox
        align (0.5, 0.3)
        spacing 5
        button:
            xysize (106,64)
            selected not preferences.fullscreen
            action Preference("display", "window")
            background "gui/setting/window_[prefix_].png"
            hover_background  "gui/setting/hover_window_[prefix_].png"
            
        null width 200
        button:
            xysize (106,64)
            action Preference("display", "fullscreen")
            background "gui/setting/fullscreen_[prefix_].png"
            hover_background  "gui/setting/hover_fullscreen_[prefix_].png"
    frame:

        hbox:
            xalign 0.5

            button:
                background "gui/history/return.png"
                hover_background "gui/history/return_hover.png"
                style "base_button"
                text _("返回"):
                    size 45
                    color "#fff"
                    hover_color "#d37b93"
                    align (0.5, 0.5)

                xysize (230,99)
                pos (1700,640)
                action Return()

            button:
                background "gui/history/return.png"
                hover_background "gui/history/return_hover.png"
                style "base_button"
                text _("返回标题页"):
                    size 45
                    color "#fff"
                    hover_color "#d37b93"
                    align (0.5, 0.5)

                xysize (230,99)
                pos (1460,750)
                if main_menu:
                    action Return()
                else:
                    action MainMenu()
    frame:
        hbox:
            button:
                pos(1280,200)
                background "gui/save/button.png"
                hover_background "gui/save/button_hover.png"
                xysize (232, 101)
                text _("恢复默认"):
                    size 50
                    color "#fff"
                    hover_color "#d37b93"
                    align (0.5, 0.5)
                action Preference("reset")
            # title


            
style volume_bar:
    xysize (380, 30)
    xmaximum 380
    left_bar "gui/volume/left.png"
    right_bar "gui/volume/right.png"
    thumb "gui/volume/thumb.png"
    hover_thumb "gui/volume/thumb_hover.png"

style volume_text:
    color "#68535a"



