status = Column(Enum(StatusItem), default=StatusItem.NAO_CONFERIDO)

quantidade_contada = Column(Integer, default=0)