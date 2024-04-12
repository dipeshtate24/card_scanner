import os
from glob import glob
import cv2
import numpy as np
from imutils.perspective import four_point_transform

# # Define the directory where you want to save the images
# upload_directory = 'C:/Users/Dipesh/PycharmProjects/pythonProject2/Visiting_card_NLP/Upload'

# image_counter = 0

# existing_files = os.listdir(upload_directory)


def resize_image(img):
    # shape of image
    width, height = img.shape[:2]

    # resize the image
    if width > 2000:
        width = 500
        # get width and height
        h, w, c = img.shape
        height = int((h / w) * width)
        size = (width, height)
        image_resize = cv2.resize(img, (width, height))
    else:
        image_resize = img

    return image_resize


def document_scanner(image_paths):
    # global image_counter  # Declare image_counter as global

    # original image path
    original_img = cv2.imread(image_paths)

    # Resize the input image
    resized_img = resize_image(original_img)

    # Convert resized image into gray scale
    img_gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)

    # Gray scale image convert into blur image
    img_blur = cv2.GaussianBlur(img_gray, (3, 3), 0)

    # Edge detection
    img_edged = cv2.Canny(img_blur, 75, 250)

    # Morphological Transform
    kernel = np.ones((5, 5), np.uint8)
    dilate = cv2.dilate(img_edged, kernel, iterations=1)
    closing = cv2.morphologyEx(dilate, cv2.MORPH_CLOSE, kernel)

    # Apply binary threshold
    ret, thresh = cv2.threshold(closing, 0, 255, cv2.THRESH_BINARY)

    # Detect the contours with binary image using cv2.APPROX_NONE
    contours, hierarchy = cv2.findContours(thresh, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)

    biggest_contour = None
    max_area = 0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1000:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.015 * peri, True)
            if area > max_area and len(approx) == 4:
                biggest_contour = approx
                max_area = area

        if biggest_contour is not None:
            rect = cv2.minAreaRect(biggest_contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            # Draw the contour on original image
            # cv2.drawContours(resized_img, [box], 0, (0, 255, 0), 2)

            # Perform perspective transformation
            wrap_img = four_point_transform(resized_img, box)

            gaussian_blur = cv2.GaussianBlur(wrap_img, (7, 7), 2)

            sharpened = cv2.addWeighted(wrap_img, 1.5, gaussian_blur, -0.5, 0)

            return sharpened
            # while f'{image_counter:03d}.jpg' in existing_files:
            #     image_counter += 1
            #
            #     image_save_path = os.path.join(upload_directory, f'{image_counter:03d}.jpg')
            #     cv2.imwrite(image_save_path, sharpened1)
            #     image_counter += 1

# # Get image paths
# image_paths = glob('C:/Users/Dipesh/PycharmProjects/pythonProject2/Upload/*')
#
# # Process images
# document_scanner(image_paths)
