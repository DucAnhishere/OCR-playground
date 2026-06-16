import React, { useState } from 'react';
import { Store, Mail, Phone, Calendar, Banknote, FileCode, Check, Copy } from 'lucide-react';

const StructuredResult = ({ data, detectedTables = [] }) => {
  const [copied, setCopied] = useState(false);

  const hasData = data && Object.keys(data).length > 0;
  const hasTables = detectedTables && detectedTables.length > 0;

  if (!hasData && !hasTables) {
    return (
      <div className="glass-card" style={{ padding: '2rem', textAlign: 'center', color: '#9ca3af' }}>
        <p>Bắt đầu quét OCR hóa đơn/tài liệu để xem kết quả bóc tách thông tin có cấu trúc</p>
      </div>
    );
  }

  const copyToClipboard = () => {
    const combinedData = {
      structured_fields: data || {},
      detected_tables: detectedTables
    };
    navigator.clipboard.writeText(JSON.stringify(combinedData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getFieldClass = (value) => {
    return value === "Không phát hiện" ? "field-value missing" : "field-value";
  };

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.75rem' }}>
        <h3 className="viewer-title" style={{ margin: 0 }}>
          <FileCode size={18} style={{ color: '#10b981' }} />
          Trích Xuất Thông Tin Có Cấu Trúc (Structured Parser)
        </h3>
        <button className="btn-secondary" onClick={copyToClipboard} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
          {copied ? <Check size={14} style={{ color: '#10b981' }} /> : <Copy size={14} />}
          {copied ? 'Đã copy!' : 'Copy JSON'}
        </button>
      </div>

      {/* Grid view of parsed cards (Only if commercial fields exist) */}
      {hasData && (
        <div className="structured-grid">
          
          {/* Merchant Name */}
          <div className="parse-field-card">
            <div className="field-icon-box merchant">
              <Store size={20} />
            </div>
            <div className="field-content">
              <span className="field-label">Tên Cửa Hàng (Merchant)</span>
              <span className={getFieldClass(data.merchant_name)}>{data.merchant_name}</span>
            </div>
          </div>

          {/* Email */}
          <div className="parse-field-card">
            <div className="field-icon-box email">
              <Mail size={20} />
            </div>
            <div className="field-content">
              <span className="field-label">Địa Chỉ Email</span>
              <span className={getFieldClass(data.email)}>{data.email}</span>
            </div>
          </div>

          {/* Phone number */}
          <div className="parse-field-card">
            <div className="field-icon-box phone">
              <Phone size={20} />
            </div>
            <div className="field-content">
              <span className="field-label">Số Điện Thoại</span>
              <span className={getFieldClass(data.phone_number)}>{data.phone_number}</span>
            </div>
          </div>

          {/* Date */}
          <div className="parse-field-card">
            <div className="field-icon-box date">
              <Calendar size={20} />
            </div>
            <div className="field-content">
              <span className="field-label">Ngày Tháng Hóa Đơn</span>
              <span className={getFieldClass(data.date)}>{data.date}</span>
            </div>
          </div>

          {/* Total Amount */}
          <div className="parse-field-card" style={{ gridColumn: 'span 2' }}>
            <div className="field-icon-box total">
              <Banknote size={20} />
            </div>
            <div className="field-content">
              <span className="field-label">Tổng Tiền Thanh Toán (Total Amount)</span>
              <span className={getFieldClass(data.total_amount)} style={{ fontSize: '1.25rem', color: '#10b981', fontWeight: 800 }}>
                {data.total_amount}
              </span>
            </div>
          </div>

        </div>
      )}

      {/* Reconstructed HTML Tables Section */}
      {hasTables && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
          <p style={{ fontSize: '0.8rem', color: '#a855f7', fontWeight: 700, marginBottom: '0.25rem', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>📊 Bảng Biểu Khôi Phục (HTML từ PP-Structure V3)</span>
          </p>
          {detectedTables.map((table) => (
            <div key={table.id} className="detected-table-wrapper" style={{
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              padding: '1.25rem',
              borderRadius: '8px',
              overflowX: 'auto',
            }}>
              <div 
                className="structure-table-container"
                dangerouslySetInnerHTML={{ __html: table.html }} 
              />
            </div>
          ))}
        </div>
      )}

      {/* JSON preview */}
      <div style={{ marginTop: '0.5rem' }}>
        <p style={{ fontSize: '0.8rem', color: '#9ca3af', fontWeight: 600, marginBottom: '0.5rem', textTransform: 'uppercase' }}>
          JSON Output (Từ Thuật Toán Hậu Xử Lý)
        </p>
        <pre style={{
          background: 'rgba(0, 0, 0, 0.2)',
          border: '1px solid rgba(255,255,255,0.05)',
          padding: '1rem',
          borderRadius: '8px',
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          overflowX: 'auto',
          color: '#a5b4fc',
          maxHeight: '220px'
        }}>
          {JSON.stringify({
            structured_fields: data || {},
            detected_tables: detectedTables
          }, null, 2)}
        </pre>
      </div>

    </div>
  );
};

export default StructuredResult;
