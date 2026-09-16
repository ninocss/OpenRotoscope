from __future__ import annotations

from pathlib import Path


def fusion_removal_comp_text(sequence_path: Path, frame_count: int) -> str:
    filename = str(sequence_path).replace("\\", "\\\\").replace('"', '\\"')
    last = max(0, frame_count - 1)
    return f'''Composition {{
    CurrentTime = 0,
    RenderRange = {{ 0, {last} }},
    GlobalRange = {{ 0, {last} }},
    Tools = ordered() {{
        MediaIn1 = MediaIn {{
            Extent_Set = true,
            ViewInfo = OperatorInfo {{ Pos = {{ 0, 0 }} }},
        }},
        OpenRotoRemoval = Loader {{
            Clips = {{
                Clip {{
                    ID = "Clip1",
                    Filename = "{filename}",
                    FormatID = "PNGFormat",
                    StartFrame = 0,
                    Length = {frame_count},
                    LengthSetManually = true,
                    TrimIn = 0,
                    TrimOut = {last},
                    ExtendFirst = 0,
                    ExtendLast = 0,
                    Loop = 0,
                    AspectMode = 0,
                    Depth = 0,
                    TimeCode = 0,
                    GlobalStart = 0,
                    GlobalEnd = {last}
                }}
            }},
            Inputs = {{ Clip = Input {{ Value = FuID {{ "Clip1" }} }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 150, 0 }} }},
        }},
        MediaOut1 = MediaOut {{
            Inputs = {{ Input = Input {{ SourceOp = "OpenRotoRemoval", Source = "Output" }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 300, 0 }} }},
        }}
    }}
}}
'''
