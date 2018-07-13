#include <llvm/IR/Module.h>
#include <llvm/IR/InstIterator.h>
#include <llvm/IR/DataLayout.h>
#include "MemAccess.h"

using namespace llvm;

static inline const DataLayout &getDL(Instruction &I) {
    return I.getModule()->getDataLayout();
}

static inline Constant *getInt(Instruction &I, unsigned N) {
    return ConstantInt::get(getDL(I).getLargestLegalIntType(I.getContext()), N);
}

MemRead::MemRead(LoadInst &LI)
    : MemAccess(LI,
        LI.getPointerOperand(),
        getInt(LI, getDL(LI).getTypeStoreSize(LI.getType())),
        LI.getAlignment(),
        true) {}

MemRead::MemRead(MemTransferInst &MT)
    : MemAccess(MT, MT.getRawSource(), MT.getLength(), MT.getAlignment(), true) {}

MemRead::MemRead(AtomicCmpXchgInst &CX)
    : MemAccess(CX,
        CX.getPointerOperand(),
        getInt(CX, getDL(CX).getTypeStoreSize(CX.getCompareOperand()->getType())),
        CX.getPointerOperand()->getPointerAlignment(getDL(CX)),
        true) {}

MemRead::MemRead(AtomicRMWInst &RMW)
    : MemAccess(RMW,
        RMW.getPointerOperand(),
        getInt(RMW, getDL(RMW).getTypeStoreSize(RMW.getValOperand()->getType())),
        RMW.getPointerOperand()->getPointerAlignment(getDL(RMW)),
        true) {}

const MemRead MemRead::Create(Instruction &I) {
    if (LoadInst *LI = dyn_cast<LoadInst>(&I))
        return MemRead(*LI);
    if (MemTransferInst *MT = dyn_cast<MemTransferInst>(&I))
        return MemRead(*MT);
    if (AtomicCmpXchgInst *CX = dyn_cast<AtomicCmpXchgInst>(&I))
        return MemRead(*CX);
    if (AtomicRMWInst *RMW = dyn_cast<AtomicRMWInst>(&I))
        return MemRead(*RMW);
    return MemRead();
}

MemRead::MemRead(Instruction &I) : MemAccess() {
    if (LoadInst *LI = dyn_cast<LoadInst>(&I))
        *this = MemRead(*LI);
    else if (MemTransferInst *MT = dyn_cast<MemTransferInst>(&I))
        *this = MemRead(*MT);
    else if (AtomicCmpXchgInst *CX = dyn_cast<AtomicCmpXchgInst>(&I))
        *this = MemRead(*CX);
    else if (AtomicRMWInst *RMW = dyn_cast<AtomicRMWInst>(&I))
        *this = MemRead(*RMW);
}

MemWrite::MemWrite(StoreInst &SI)
    : MemAccess(SI,
        SI.getPointerOperand(),
        getInt(SI, getDL(SI).getTypeStoreSize(SI.getValueOperand()->getType())),
        SI.getAlignment(),
        false) {}

MemWrite::MemWrite(MemIntrinsic &MI)
    : MemAccess(MI, MI.getRawDest(), MI.getLength(), MI.getAlignment(), false) {}

MemWrite::MemWrite(AtomicCmpXchgInst &CX)
    : MemAccess(CX,
        CX.getPointerOperand(),
        getInt(CX, getDL(CX).getTypeStoreSize(CX.getCompareOperand()->getType())),
        CX.getPointerOperand()->getPointerAlignment(getDL(CX)),
        false) {}

MemWrite::MemWrite(AtomicRMWInst &RMW)
    : MemAccess(RMW,
        RMW.getPointerOperand(),
        getInt(RMW, getDL(RMW).getTypeStoreSize(RMW.getValOperand()->getType())),
        RMW.getPointerOperand()->getPointerAlignment(getDL(RMW)),
        false) {}

const MemWrite MemWrite::Create(Instruction &I) {
    if (StoreInst *SI = dyn_cast<StoreInst>(&I))
        return MemWrite(*SI);
    if (MemIntrinsic *MI = dyn_cast<MemIntrinsic>(&I))
        return MemWrite(*MI);
    if (AtomicCmpXchgInst *CX = dyn_cast<AtomicCmpXchgInst>(&I))
        return MemWrite(*CX);
    if (AtomicRMWInst *RMW = dyn_cast<AtomicRMWInst>(&I))
        return MemWrite(*RMW);
    return MemWrite();
}

MemWrite::MemWrite(Instruction &I) {
    if (StoreInst *SI = dyn_cast<StoreInst>(&I))
        *this = MemWrite(*SI);
    else if (MemIntrinsic *MI = dyn_cast<MemIntrinsic>(&I))
        *this = MemWrite(*MI);
    else if (AtomicCmpXchgInst *CX = dyn_cast<AtomicCmpXchgInst>(&I))
        *this = MemWrite(*CX);
    else if (AtomicRMWInst *RMW = dyn_cast<AtomicRMWInst>(&I))
        *this = MemWrite(*RMW);
}
