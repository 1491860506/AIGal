## Put style definitions preferably in gui.rpy or near the top of screens.rpy
## Adjust fonts, sizes, colors, and padding as needed

style main_menu_frame:
    # Makes the frame containing title and buttons fill the screen
    # Adjust margins if your background image has borders you want to avoid
    xmargin 50
    ymargin 50
    background None
    # Often doesn't need specific styling if elements inside are positioned correctly

style main_menu_title_text:
    # Style for the game title (config.name)
    size 120                # Adjust size
    color "#eb1111"            # White color, adjust as needed
    hover_color "#FFFF00"      # Example hover color (optional for title)
    outlines [(2, "#000000", 0, 0)] # Optional outline for better visibility
    text_align 0.5             # Center align text (redundant with xalign 0.5 on widget?)
    font "/fonts/niwobuqieyu.ttf"
    # Add more properties like bold, italics, etc. if desired

style main_menu_navigation_box:
    # Style for the hbox containing the buttons
    # Position the box itself
    xalign 0.5                 # Center horizontally
    yalign 0.90                # Position near the bottom (adjust 0.0 top to 1.0 bottom)
    # yoffset -50              # Optional fine-tuning offset from the yalign position
    spacing 0                # Space between buttons

style main_menu_button is default:
    # Base style for navigation buttons
    # size_group "main_menu"     # Uncomment if you want all buttons to have the same width
    background None            # No background by default (text only)
    padding (20, 10)           # Horizontal, Vertical padding around the text

style main_menu_button_text is default:
    # Style for the text inside the buttons
    size 66                    # Adjust size
    color "#220cb6"            # Idle text color (light gray)
    hover_color "#FFFFFF"      # Hover text color (white)
    # Add a subtle hover effect using text properties
    hover_outlines [(1, "#FFFFFF", 0, 0)] # Add a subtle white outline on hover
    # idle_outlines []         # Ensure no outline when idle if you add hover_outlines
    # You can also change hover_size slightly for a zoom effect
    # hover_size 30

    # Add transitions for smoother hover effects (optional)
    # properties { "color": Animation("gui/button/text_idle_color.png", 0.1, "gui/button/text_hover_color.png", 0.1),
    #              "outlines": Animation("[]", 0.1, "[(1, \"#FFFFFF\", 0, 0)]", 0.1) }


image main_menu_background1 = Solid("#9d9a9a90", xysize=(1400,100), pos=(250,840))
## Main Menu screen ############################################################

## Define the background image (make sure the path is correct)

## Main Menu screen ############################################################

## 定义按钮的图标路径（注意替换为您的实际图标路径）
image icon_start = "/gui/icons/start.png"
image icon_load = "/gui/icons/load.png"
image icon_settings = "/gui/icons/settings.png"
image icon_quit = "/gui/icons/quit.png"

screen main_menu():

    ## This ensures that any other menu screen is replaced.
    tag menu

    ## Add the background image
    add "main_menu_background"
    add "main_menu_background1"
    ## Use a frame to help structure content, though you could place items directly
    frame:
        style "main_menu_frame" # Apply the frame style (mostly for positioning scope)
        # Display the game title using config.name
        text config.window_title:
            style "main_menu_title_text"
            xalign 0.5  # Center horizontally
            yalign 0.2  # Position near the top (adjust 0.0 top to 1.0 bottom)

        # Horizontal box for navigation buttons, positioned according to the layout
        hbox:
            style "main_menu_navigation_box" # Apply positioning and spacing style

            # --- Navigation Buttons ---
            # Apply the button style and text style to each textbutton
            add "icon_start"
            textbutton _("开始游戏") action Start(): 
                style "main_menu_button"
                text_style "main_menu_button_text"
            text "    "
            add "icon_load"
            textbutton _("读取") action ShowMenu("load"): 
                style "main_menu_button"
                text_style "main_menu_button_text"
            text "    "
            add "icon_settings"
            textbutton _("设置") action ShowMenu("preferences"): 
                style "main_menu_button"
                text_style "main_menu_button_text"
            text "    "
            add "icon_quit"
            # Quit button (only shown on platforms where quitting is standard)
            if renpy.variant("pc"):
                textbutton _("退出") action Quit(confirm=True): 
                    style "main_menu_button"
                    text_style "main_menu_button_text"

            # --- Add other platform conditions if needed ---
            # Example for Web/Mobile if you want Quit differently or not at all
            # if renpy.variant("web") or renpy.variant("mobile"):
            #     pass # Or add a different button/action if applicable