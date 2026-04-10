import numpy as np
   from core.align import AlignFallbackChain
   from core.models import ROIConfig
   img = np.zeros((200,200,3), dtype='uint8')
   chain = AlignFallbackChain(image_store=None, roi_config=None)
   result = chain.run(img)
   print('strategy:', result.strategy)
   print('success:', result.success)
   print('design_doc:', result.design_doc)
