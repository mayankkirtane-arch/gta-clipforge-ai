import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.clip import Clip
from ..models.recording import Recording
from ..schemas.publishing import ExportPackageRequest, ExportPackageResponse
from ..services.export_service import export_service

router = APIRouter(prefix="/api/exports", tags=["exports"])

@router.get("/clips/{clip_id}/subtitles.srt")
def get_clip_srt_subtitles(clip_id: int, download: bool = False, db: Session = Depends(get_db)):
    """Generate and return synchronized SRT subtitles for a Short."""
    try:
        srt_content = export_service.generate_srt_subtitles(db, clip_id)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="short_{clip_id}.srt"'
        return PlainTextResponse(content=srt_content, media_type="text/plain; charset=utf-8", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SRT subtitles: {str(e)}")

@router.get("/clips/{clip_id}/transcript.txt")
def get_clip_txt_transcript(clip_id: int, download: bool = False, db: Session = Depends(get_db)):
    """Generate and return clean readable text transcript for a Short."""
    try:
        txt_content = export_service.generate_txt_transcript(db, clip_id)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="short_{clip_id}_transcript.txt"'
        return PlainTextResponse(content=txt_content, media_type="text/plain; charset=utf-8", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate transcript: {str(e)}")

@router.get("/metadata.csv")
def export_metadata_csv(
    clip_ids: Optional[str] = Query(None, description="Comma-separated clip IDs"),
    db: Session = Depends(get_db)
):
    """Generate and download complete CSV metadata for Shorts catalog."""
    c_ids = None
    if clip_ids:
        try:
            c_ids = [int(x.strip()) for x in clip_ids.split(",") if x.strip()]
        except Exception:
            pass

    csv_content = export_service.export_csv_metadata(db, c_ids)
    headers = {"Content-Disposition": 'attachment; filename="GTA6_SHORTS_METADATA.csv"'}
    return Response(content=csv_content, media_type="text/csv; charset=utf-8", headers=headers)

@router.get("/reports/{recording_id}")
def get_copyright_report(recording_id: int, format: str = "markdown", db: Session = Depends(get_db)):
    """Get or generate copyright and compliance report for a recording."""
    try:
        rep = export_service.generate_copyright_report(db, recording_id)
        if format.lower() == "json":
            return FileResponse(rep["json_path"], media_type="application/json")
        return FileResponse(rep["markdown_path"], media_type="text/markdown")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate copyright report: {str(e)}")

@router.post("/best-moments/{recording_id}")
def export_best_moments(recording_id: int, db: Session = Depends(get_db)):
    """Extract raw horizontal best moment clips into GTA6_BEST_MOMENTS folder."""
    try:
        moments = export_service.export_best_moments(db, recording_id)
        return {
            "status": "success",
            "recording_id": recording_id,
            "exported_count": len(moments),
            "moments": moments,
            "target_directory": str(export_service.best_moments_dir)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export best moments: {str(e)}")

@router.post("/package-zip", response_model=ExportPackageResponse)
def create_export_package(req: ExportPackageRequest, db: Session = Depends(get_db)):
    """Package selected or approved Shorts, SRTs, transcripts, CSV, and reports into a production ZIP archive."""
    try:
        res = export_service.create_export_zip(
            db=db,
            clip_ids=req.clip_ids,
            include_subtitles=req.include_subtitles_srt,
            include_transcripts=req.include_transcripts_txt,
            include_metadata=req.include_metadata_csv,
            include_copyright_reports=req.include_copyright_reports,
            package_name=req.package_name
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build export package: {str(e)}")

@router.get("/download/{zip_filename}")
def download_zip_package(zip_filename: str):
    """Download generated export ZIP package from GTA6_EXPORTS."""
    zip_path = export_service.exports_dir / zip_filename
    if not zip_path.is_file():
        raise HTTPException(status_code=404, detail="Export package file not found")
    return FileResponse(zip_path, media_type="application/zip", filename=zip_filename)
