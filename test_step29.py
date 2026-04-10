import cv2, numpy as np
from core.align.feature_align import FeatureAlignEngine
from core.align.contour_align import ContourAlignEngine
from core.align.blob_align import BlobAlignEngine

img = cv2.imread('tests/fixtures/sample_ok.png')

eng = FeatureAlignEngine()
r = eng.align(img, img)
eng.save_overlay_image('/tmp/feature_result.png')
print('Feature score:', r.match_score)

eng2 = ContourAlignEngine()
r2 = eng2.align(img, img)
eng2.save_overlay_image('/tmp/contour_result.png')
print('Contour score:', r2.match_score)

eng3 = BlobAlignEngine()
r3 = eng3.align(img, img)
eng3.save_overlay_image('/tmp/blob_result.png')
print('Blob score:', r3.match_score)
