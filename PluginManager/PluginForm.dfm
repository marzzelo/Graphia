object PluginFrm: TPluginFrm
  Left = 0
  Top = 0
  BorderIcons = []
  Caption = 'Plugin Manager'
  ClientHeight = 361
  ClientWidth = 384
  Color = clBtnFace
  Constraints.MinHeight = 300
  Constraints.MinWidth = 280
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -11
  Font.Name = 'Tahoma'
  Font.Style = []
  OldCreateOrder = False
  Position = poMainFormCenter
  PixelsPerInch = 96
  TextHeight = 13
  object Splitter1: TSplitter
    Left = 0
    Top = 205
    Width = 384
    Height = 3
    Cursor = crVSplit
    Align = alTop
    Beveled = True
    ExplicitTop = 200
  end
  object ListView: TListView
    AlignWithMargins = True
    Left = 8
    Top = 8
    Width = 368
    Height = 189
    Margins.Left = 8
    Margins.Top = 8
    Margins.Right = 8
    Margins.Bottom = 8
    Align = alTop
    Columns = <
      item
        AutoSize = True
        Caption = 'Plugin name'
      end
      item
        AutoSize = True
        Caption = 'Version'
      end>
    ColumnClick = False
    ReadOnly = True
    RowSelect = True
    SortType = stText
    TabOrder = 0
    ViewStyle = vsReport
  end
  object Panel1: TPanel
    Left = 0
    Top = 208
    Width = 384
    Height = 153
    Align = alClient
    TabOrder = 1
    DesignSize = (
      384
      153)
    object Label1: TLabel
      Left = 8
      Top = 9
      Width = 26
      Height = 13
      Caption = 'Path:'
    end
    object Memo: TMemo
      Left = 8
      Top = 33
      Width = 368
      Height = 81
      Anchors = [akLeft, akTop, akRight, akBottom]
      Color = clBtnFace
      ScrollBars = ssVertical
      TabOrder = 1
      WantReturns = False
    end
    object PathEdit: TEdit
      Left = 40
      Top = 6
      Width = 336
      Height = 21
      Anchors = [akLeft, akTop, akRight]
      Color = clBtnFace
      ReadOnly = True
      TabOrder = 0
    end
    object ImportButton: TButton
      Left = 125
      Top = 120
      Width = 75
      Height = 25
      Anchors = [akRight, akBottom]
      Caption = 'Import'
      TabOrder = 2
    end
    object UninstallButton: TButton
      Left = 213
      Top = 120
      Width = 75
      Height = 25
      Anchors = [akRight, akBottom]
      Caption = 'Uninstall'
      Enabled = False
      TabOrder = 3
    end
    object CloseButton3: TButton
      Left = 301
      Top = 120
      Width = 75
      Height = 25
      Anchors = [akRight, akBottom]
      Cancel = True
      Caption = 'Close'
      ModalResult = 2
      TabOrder = 4
    end
  end
end
