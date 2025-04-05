import cv2
import numpy as np
import os
import time
import sys   # Import the sys module

def method_a(image,
    target_width,
    target_height,
    strategy):
    try:
        with open(image, 'rb') as f:
            img_data = np.frombuffer(f.read(), dtype=np.uint8)
        image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        # 预处理流程（增加gamma校正提升对比度）
        target_size = (256, 256)
        pass_threshold = 0.1
        var_threshold = 1.0
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Gamma校正（补偿对比度影响）
        gamma = 0.8  # 可调参数，小于1增强暗部细节
        gray = np.uint8(((gray/255.0) ** gamma) * 255)

        # 分辨率归一化
        resized = cv2.resize(gray, target_size, interpolation=cv2.INTER_AREA)
        
        # 改进的归一化（保持原始动态范围）
        normalized = resized.astype(np.float32) / 255.0

        # Sobel算子标准化（修正梯度缩放问题）
        scale_ratio = 0.25  # 关键修正！Sobel结果需要缩放
        grad_x = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3) * scale_ratio
        grad_y = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3) * scale_ratio
        
        # 梯度幅值计算
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # 动态方差阈值（根据图像对比度自适应）
        global_var = np.var(normalized)
        dynamic_var_threshold = max(0.5, global_var * 2)  # 自适应调整
        
        # 优化局部方差计算（使用积分图加速）
        kernel_size = 16  # 增大窗口尺寸避免细节遗漏
        sum_kernel = np.ones((kernel_size, kernel_size), np.float32)
        
        # 积分图计算
        sum_ = cv2.filter2D(normalized, -1, sum_kernel) / (kernel_size**2)
        sum_sq = cv2.filter2D(normalized**2, -1, sum_kernel) / (kernel_size**2)
        local_var = sum_sq - sum_**2
        
        # 生成动态掩码
        mask = (local_var > (dynamic_var_threshold / 255.0**2))
        
        if np.sum(mask) < 100:  # 有效区域最小像素保护
            mask = (local_var > 0)  # 回退到全图计算
        
        # 计算有效区域梯度（增加权重机制）
        masked_gradient = gradient_magnitude[mask]
        sharpness_score = np.percentile(masked_gradient, 90)  # 使用90%分位数代替均值
        
        # 分数标准化（修正量纲问题）
        max_possible = np.sqrt(2*(1.0**2))  # 理论最大梯度（对角边缘）
        normalized_score = (sharpness_score / max_possible) * 100  # 转换为百分比
    except:
        normalized_score=0


    sys.exit(int(normalized_score))

def preprocess_image(img_path):
    # 支持中文路径的读取方式
    with open(img_path, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img=cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    
    # 分离透明通道处理
    if img is None:
        raise ValueError("无法读取图像文件，请检查路径和文件格式")

    # 通道数判断（修复部分图片没有透明通道时的判断逻辑）
    if len(img.shape) == 2:  # 灰度图处理
        gray = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        return cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY), img.shape[0], img.shape[1]
        
    if img.shape[2] == 4:
        alpha = img[:, :, 3]
        rgb = img[:, :, :3]
        # 修复OpenCV的BGR问题
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        bg = np.ones_like(rgb) * 255
        mask = alpha[:, :, np.newaxis] / 255.0
        img = (rgb * mask + bg * (1 - mask)).astype(np.uint8)
    else:
        # 转换BGR到RGB（针对普通三通道图片）
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return gray, img.shape[0], img.shape[1]

def method_b(img_path,
    target_width,
    target_height,
    strategy):
    gray, h, w = preprocess_image(img_path)
    try:
        # 使用Sobel算子计算梯度
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        score = np.mean(gx**2 + gy**2)
        
        # 基于分辨率的基准值
        resolution_baselines = {
            (1024, 1024): 350.0,  # 对应人物图的基准值
            (1080, 1920): 550.0   # 对应背景图的基准值
        }
        
        key = (h, w) if (h, w) in resolution_baselines else (w, h)
        baseline = resolution_baselines.get(key, 400.0)
        final_score = min(score / baseline,100)
    except:
        final_score = 0
    sys.exit(int(final_score))


def method_c(img_path,
    target_width,
    target_height,
    strategy):
    try:
        gray, h, w = preprocess_image(img_path)
        
        # 增加高斯模糊预处理（消除微小噪声影响）
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        laplacian_var = cv2.Laplacian(blurred, cv2.CV_64F).var()
        
        # 动态基准值计算
        resolution_factor = (h * w) / (1024*1024)
        baseline = 200 * resolution_factor**0.75

        final_score = np.clip(laplacian_var / baseline * 100, 0, 100)
    except:
        final_score=0
    sys.exit(int(final_score))

def resize_image_strategy(
    image_path,
    target_width,
    target_height,
    strategy
):
    """
    Resizes an image to target dimensions using a specified strategy,
    handling transparency (4 channels) correctly and overwrites the original file.

    Args:
        image_path (str): Path to the input image (can contain Chinese characters).
        target_width (int): Desired output width.
        target_height (int): Desired output height.
        strategy (str): The resizing strategy: 'crop', 'pad', or 'stretch'.

    Returns:
        bool: True on success, False on failure.
    """
    inpaint_radius = 5  # Default inpaint radius - removed as a parameter

    # --- 1. Read Image (Handling Chinese Path and Transparency) ---
    try:
        image_bytes = np.fromfile(image_path, dtype=np.uint8)
        # Read with UNCHANGED to keep alpha channel if present
        image = cv2.imdecode(image_bytes, cv2.IMREAD_UNCHANGED)
        if image is None:
            print(f"Error: Could not read image at {image_path}")
            return False
    except Exception as e:
        print(f"Error reading file {image_path}: {e}")
        return False

    original_height, original_width = image.shape[:2]
    # Check if image has 4 channels (BGRA)
    has_alpha = len(image.shape) > 2 and image.shape[2] == 4
    print(f"Original dimensions: {original_width}x{original_height}, Alpha: {has_alpha}")

    # --- 2. Check if Already Target Size ---
    if original_width == target_width and original_height == target_height:
        print(f"Image is already at the target resolution {target_width}x{target_height}. No changes needed.")
        print(f"No changes made to {image_path}.")
        return True  # No need to save (no changes)

    target_ratio = target_width / target_height
    original_ratio = original_width / original_height
    processed_image = None

    # --- 3. Apply Strategy ---
    if strategy == 'stretch':
        print("Applying 'stretch' strategy...")
        processed_image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)

    elif strategy == 'crop':
        print("Applying 'crop' strategy...")
        temp_image = image.copy()  # Work on a copy to preserve original

        if abs(original_ratio - target_ratio) > 1e-5:  # Check if cropping is needed
            if original_ratio > target_ratio:
                # Wider than target ratio, crop width
                new_width = int(original_height * target_ratio)
                start_x = (original_width - new_width) // 2
                temp_image = temp_image[:, start_x : start_x + new_width]
                print(f"Cropping width from {original_width} to {new_width}")
            else:
                # Taller than target ratio, crop height
                new_height = int(original_width / target_ratio)
                start_y = (original_height - new_height) // 2
                temp_image = temp_image[start_y : start_y + new_height, :]
                print(f"Cropping height from {original_height} to {new_height}")
        else:
            print("Image already has the target aspect ratio. No cropping needed before resize.")

        # Resize the (potentially cropped) image to the final target dimensions
        processed_image = cv2.resize(temp_image, (target_width, target_height), interpolation=cv2.INTER_AREA)

    elif strategy == 'pad':
        print("Applying 'pad' strategy using Inpainting (TELEA)...")

        if abs(original_ratio - target_ratio) < 1e-5:
            # Ratio already matches, just resize (like stretch)
            print("Image already has target ratio, performing direct resize instead of padding.")
            processed_image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)
        else:
            # Ratio mismatch, perform inpainting padding
            # Separate BGR and Alpha for inpainting (inpainting works on BGR)
            if has_alpha:
                image_bgr = image[:, :, :3]
                original_alpha = image[:, :, 3]
            else:
                image_bgr = image
                original_alpha = None  # No alpha channel to worry about

            # Determine intermediate canvas size to match target ratio
            if original_ratio > target_ratio:
                # Wider than target: Canvas height determined by original width
                canvas_height = int(original_width / target_ratio)
                canvas_width = original_width
                start_y = (canvas_height - original_height) // 2
                start_x = 0
            else:
                # Taller than target: Canvas width determined by original height
                canvas_width = int(original_height * target_ratio)
                canvas_height = original_height
                start_x = (canvas_width - original_width) // 2
                start_y = 0

            # Create BGR canvas and place image BGR part onto it
            canvas_bgr = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
            canvas_bgr[start_y : start_y + original_height, start_x : start_x + original_width] = image_bgr

            # Create mask (255 where to inpaint, 0 where original image is)
            mask = np.full((canvas_height, canvas_width), 255, dtype=np.uint8)
            mask[start_y : start_y + original_height, start_x : start_x + original_width] = 0

            # Perform Inpainting on BGR canvas
            print(f"Starting inpainting (radius={inpaint_radius})... This may take some time...")
            start_time = time.time()
            inpainted_bgr = cv2.inpaint(canvas_bgr, mask, inpaint_radius, cv2.INPAINT_TELEA)
            end_time = time.time()
            print(f"Inpainting finished in {end_time - start_time:.2f} seconds.")

            # Resize the inpainted BGR canvas to the final target size
            final_bgr = cv2.resize(inpainted_bgr, (target_width, target_height), interpolation=cv2.INTER_AREA)

            # Handle alpha channel for the final image
            if has_alpha:
                # Create a canvas for the alpha channel, matching the BGR canvas size
                canvas_alpha = np.zeros((canvas_height, canvas_width), dtype=np.uint8)  # Start transparent
                # Place original alpha onto the alpha canvas
                canvas_alpha[start_y : start_y + original_height, start_x : start_x + original_width] = original_alpha
                # Make the inpainted areas opaque (255) in the alpha canvas
                # We use the same mask but invert it (where mask==255, make alpha 255)
                canvas_alpha[mask == 255] = 255

                # Resize the combined alpha canvas to the final target size
                final_alpha = cv2.resize(canvas_alpha, (target_width, target_height), interpolation=cv2.INTER_AREA) # It is generally better with INTER_AREA than with INTER_NEAREST

                # Combine final BGR and final Alpha
                processed_image = cv2.cvtColor(final_bgr, cv2.COLOR_BGR2BGRA)
                processed_image[:, :, 3] = final_alpha
            else:
                # No original alpha, the final BGR is the result
                processed_image = final_bgr

    else:
        print(f"Error: Unknown strategy '{strategy}'. Choose 'crop', 'pad', or 'stretch'.")
        return False

    # --- 4. Save Result (Overwrite the Original) ---
    if processed_image is not None:
        try:
            file_extension = os.path.splitext(image_path)[1]
            if not file_extension:
                file_extension = '.png'  # Add default png
                image_path += file_extension

            # Ensure correct format for saving (PNG for transparency support)
            if len(processed_image.shape) > 2 and processed_image.shape[2] == 4 and file_extension.lower() not in ['.png', '.tif', '.tiff', '.webp']:
                print(f"Warning: Transparent image, forcing PNG for saving {image_path}")
                file_extension = '.png'
                image_path = os.path.splitext(image_path)[0] + file_extension # fix if not set before
            is_success, encoded_image = cv2.imencode(file_extension, processed_image)
            if not is_success:
                print(f"Error: Failed to encode and save to {image_path}")
                return False
            encoded_image.tofile(image_path)

            final_h, final_w = processed_image.shape[:2]
            print(f"Successfully processed image using '{strategy}'.")
            print(f"Final dimensions: {final_w}x{final_h}")
            print(f"Saved (overwrote) to: {image_path}")
            return True

        except Exception as e:
            print(f"Error saving (overwriting) file to {image_path}: {e}")
            return False
    else:
        print("Error: Processed image is None. Something went wrong.")
        return False

def dispatch(func_name, *args):
    """Dispatch function to call other functions by name."""
    function_mapping = {
        "resize_image_strategy": resize_image_strategy,
        "method_a":method_a,
        "method_b":method_b,
        "method_c":method_c
        # Add more functions here
    }
    if func_name in function_mapping:
        func = function_mapping[func_name]
        return func(*args)
    else:
        print(f"Error! function {func_name} not found")
        return False

if __name__ == "__main__":
    function_name = sys.argv[1]
    image_path = sys.argv[2]
    target_width = int(sys.argv[3]) # Always int
    target_height = int(sys.argv[4]) # Always int
    strategy = sys.argv[5]

    # Call Dispatch with required arguments
    dispatch(function_name, image_path, target_width, target_height, strategy)
