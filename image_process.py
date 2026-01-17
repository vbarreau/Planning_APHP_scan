import cv2
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt


def locate_quadrilaterals(img):
    """
    Locate quadrilaterals in the image.
    
    Parameters:
    img (PIL.Image): The input image.

    Returns:
    list: A list of quadrilaterals, each represented by a list of four points.
    """
    # Convert PIL image to OpenCV format
    open_cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    quadrilaterals = []
    
    for contour in contours:
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Check if the approximated contour has 4 points
        if len(approx) == 4:
            # Extract the corner points
            corners = [point[0] for point in approx] # type: ignore
            
            # Check if all edges are at least 50 pixels long
            valid = True
            for i in range(4):
                pt1 = corners[i]
                pt2 = corners[(i + 1) % 4]
                edge_length = np.linalg.norm(np.array(pt1) - np.array(pt2))
                if edge_length < 50:
                    valid = False
                    break
            
            if valid:
                quadrilaterals.append(corners)
    
    return np.array(quadrilaterals)

def perimeter(box):
    return np.sum([np.linalg.norm(box[i] - box[(i + 1) % 4]) for i in range(4)])

def quad_to_rectangle(quad):
    rect = quad.copy()  

    if abs(quad[0,0]-quad[1,0] )< abs(quad[0,1]-quad[1,1]):
        rect[1][0] = quad[0][0]
        rect[3][1] = quad[0][1]
        rect[2][1] = quad[1][1]
        rect[3][0] = quad[2][0]

    else:
        rect[1][1] = quad[0][1]
        rect[3][0] = quad[0][0]
        rect[2][0] = quad[1][0]
        rect[3][1] = quad[2][1]

    return rect

def best_rectangle(quads,img):
    box_sizes =np.array( [perimeter(box) for box in quads])
    try :
        max_perimeter = img.width/5 * 4
    except:
        max_perimeter = img.shape[1]/5 * 4
    i_out = 0
    for i in range(len(quads)):
        if box_sizes[i] > box_sizes[i_out] and box_sizes[i] < max_perimeter:
            i_out = i
    return quads[i_out]


def find_homography(quads,img):

    start_pos = best_rectangle(quads,img)
    aim_pos = quad_to_rectangle(start_pos)

    # Find the homography matrix
    homography, _ = cv2.findHomography(start_pos, aim_pos)
    return homography

def correct_perspective(img, homography):
    """
    Correct the perspective of the image.
    """

    # Apply the homography
    img = cv2.warpPerspective(img, homography, (int(img.shape[1]*1.2), int(img.shape[0]*1.2)))
    return img

def process(img):
    quadrilaterals = locate_quadrilaterals(img)
    homography = find_homography(quadrilaterals,img)
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    new_img = correct_perspective(img_cv, homography)
    return Image.fromarray(cv2.cvtColor(new_img, cv2.COLOR_BGR2RGB))


if __name__ == "__main__":
    # Load the image
    img = Image.open("image.jpg")
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    

    # draw = ImageDraw.Draw(img)
    # draw.polygon(rect, outline='red', width=5)
    # plt.imshow(img)
    # plt.show()
    # Correct the perspective of the image
    img2 = img.copy()
    for i in range(5):
        try:
            img2 = process(img2)
        except:
            print("Error, i = ", i)
            break
 

    # plt.imshow(img2_pil)
    # plt.show()
    # Display the corrected image
    fig,ax = plt.subplots(1,2, figsize=(15,5))
    ax[0].imshow(img)
    ax[1].imshow(img2)
    plt.show()

