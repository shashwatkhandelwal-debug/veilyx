#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(Veilyx, NSObject)

RCT_EXTERN_METHOD(
  initialize:(RCTPromiseResolveBlock)resolve
  withRejecter:(RCTPromiseRejectBlock)reject
)

RCT_EXTERN_METHOD(
  requestProof:(NSString *)companyName
  withChecks:(NSArray *)checks
  withAadhaar:(NSString *)aadhaarXmlData
  withResolver:(RCTPromiseResolveBlock)resolve
  withRejecter:(RCTPromiseRejectBlock)reject
)

RCT_EXTERN_METHOD(
  pickAadhaarFile:(RCTPromiseResolveBlock)resolve
  withRejecter:(RCTPromiseRejectBlock)reject
)

RCT_EXTERN_METHOD(
  readAadhaarFile:(NSString *)filePath
  withResolver:(RCTPromiseResolveBlock)resolve
  withRejecter:(RCTPromiseRejectBlock)reject
)

RCT_EXTERN_METHOD(
  handleDeepLink:(NSString *)url
  withResolver:(RCTPromiseResolveBlock)resolve
  withRejecter:(RCTPromiseRejectBlock)reject
)

RCT_EXTERN_METHOD(
  handleDigiLockerCallback:(NSString *)code
  withState:(NSString *)state
  withResolver:(RCTPromiseResolveBlock)resolve
  withRejecter:(RCTPromiseRejectBlock)reject
)

+ (BOOL)requiresMainQueueSetup
{
  return NO;
}

@end
