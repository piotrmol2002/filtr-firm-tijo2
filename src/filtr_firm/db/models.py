from datetime import date

from sqlalchemy import CheckConstraint, Date, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CompanyRow(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("source IN ('ceidg', 'krs')", name="source"),
        CheckConstraint(
            "legal_form IN ('jdg', 'sp_zoo', 'psa', 'sa', 'sk', 'ska', 'sj', 'sp', "
            "'spoldzielnia', 'other')",
            name="legal_form",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(Text)
    legal_form: Mapped[str] = mapped_column(String(16))
    voivodeship: Mapped[str | None] = mapped_column(String(32))
    city: Mapped[str | None] = mapped_column(Text)
    pkd_main: Mapped[str | None] = mapped_column(String(8))
    pkd_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String(8)), default=list, server_default=text("'{}'")
    )
    event_date: Mapped[date | None] = mapped_column(Date, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(Text)
