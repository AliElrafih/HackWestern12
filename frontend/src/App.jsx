import { useState, useRef, useEffect, useContext } from 'react'
import './App.css'
import UserContext from './contexts/UsersContext'

function App() {
  const [activeTab, setActiveTab] = useState('live-scan')
  const [selectedImage, setSelectedImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [addPreview, setAddPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [patientData, setPatientData] = useState({
    name: '',
    age: '',
    sex: '',
    height: '',
    weight: '',
    insurance: '',
    allergies: '',
    conditions: ''
  })


  const { users, addUser ,refreshUsers } = useContext(UserContext)



  const [selectedPatient, setSelectedPatient] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const videoRef = useRef(null)
  const addPatientVideoRef = useRef(null)
  const streamRef = useRef(null)
  const addPatientStreamRef = useRef(null)

  const API_URL = 'http://localhost:8000'

  // Live Scan functionality
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
      }
    } catch (err) {
      console.error('Error accessing camera:', err)
      setError('Could not access camera. Please check permissions.')
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
  }

  const capturePhoto = () => {
    if (videoRef.current) {
      const canvas = document.createElement('canvas')
      canvas.width = videoRef.current.videoWidth
      canvas.height = videoRef.current.videoHeight
      const ctx = canvas.getContext('2d')
      // Flip horizontally to correct mirror effect
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
      ctx.drawImage(videoRef.current, 0, 0)
      canvas.toBlob((blob) => {
        const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' })
        setSelectedImage(file)
        const reader = new FileReader()
        reader.onloadend = () => {
          setPreview(reader.result)
        }
        reader.readAsDataURL(file)
        identifyPatient(file)
      }, 'image/jpeg')
    }
  }

  // Add Patient camera functionality
  const startAddPatientCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      if (addPatientVideoRef.current) {
        addPatientVideoRef.current.srcObject = stream
        addPatientStreamRef.current = stream
      }
    } catch (err) {
      console.error('Error accessing camera:', err)
      setError('Could not access camera. Please check permissions.')
    }
  }

  const stopAddPatientCamera = () => {
    if (addPatientStreamRef.current) {
      addPatientStreamRef.current.getTracks().forEach(track => track.stop())
      addPatientStreamRef.current = null
    }
  }

  const captureAddPatientPhoto = () => {
    if (addPatientVideoRef.current) {
      const canvas = document.createElement('canvas')
      canvas.width = addPatientVideoRef.current.videoWidth
      canvas.height = addPatientVideoRef.current.videoHeight
      const ctx = canvas.getContext('2d')
      // Flip horizontally to correct mirror effect
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
      ctx.drawImage(addPatientVideoRef.current, 0, 0)
      canvas.toBlob((blob) => {
        const file = new File([blob], 'patient-photo.jpg', { type: 'image/jpeg' })
        setSelectedImage(file)
        const reader = new FileReader()
        reader.onloadend = () => {
          setAddPreview(reader.result)
        }
        reader.readAsDataURL(file)
        stopAddPatientCamera()
      }, 'image/jpeg')
    }
  }

  useEffect(() => {
    if (activeTab === 'live-scan') {
      startCamera()
      stopAddPatientCamera()
    } else if (activeTab === 'add-patient') {
      stopCamera()
      if (!addPreview) {
        startAddPatientCamera()
      }
    } else {
      stopCamera()
      stopAddPatientCamera()
    }
    return () => {
      stopCamera()
      stopAddPatientCamera()
    }
  }, [activeTab, preview, addPreview])

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedImage(file)
      setResult(null)
      setError(null)
      
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const identifyPatient = async (imageFile = selectedImage) => {
    if (!imageFile) {
      setError('Please select an image first')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('image', imageFile)

    try {
      const response = await fetch(`${API_URL}/identify`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      
      if (response.ok) {
        setResult(data)
      } else {
        console.log(data)
        setError(data.reason || 'Failed to identify patient')
        setResult({ match_found: false, reason: data.reason || 'Failed to identify patient' })
      }
    } catch (err) {
      setError('Failed to connect to server. Make sure the backend is running.')
      setResult({ match_found: false, reason: 'Failed to connect to server' })
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAddPatient = () => {
    if (!addPreview || !patientData.name) {
      setError('Please provide patient photo and name')
      return
    }

    const newPatient = {
      id: Date.now(),
      name: patientData.name,
      profile_pic: selectedImage,
      ...patientData,
      dateAdded: new Date().toLocaleDateString()
    }

  
    addUser(newPatient)
    setPatientData({
      name: '',
      age: '',
      sex: '',
      height: '',
      weight: '',
      insurance: '',
      allergies: '',
      conditions: ''
    })
    setAddPreview(null)
    setSelectedImage(null)
    setError(null)
    // Restart camera for next patient
    setTimeout(() => {
      if (activeTab === 'add-patient') {
        startAddPatientCamera()
      }
    }, 100)
    alert('Patient added successfully!')
  }

  const renderLiveScan = () => (
    <div className="live-scan-page">
      <div className="page-header">
        <h2>Live Scan</h2>
        <p className="page-description">
          Live Scan of a patients face, Compared with database information and returning relevant medical information.
        </p>
      </div>

      <div className="live-scan-content">
        <div className="camera-section">
          <div className="camera-container">
            {preview ? (
              <div className="image-preview-container">
                <img src={preview} alt="Captured" />
                <button className="retake-btn" onClick={() => {
                  setPreview(null)
                  setSelectedImage(null)
                  setResult(null)
                  startCamera()
                }}>Retake</button>
              </div>
            ) : (
              <>
                <video ref={videoRef} autoPlay playsInline className="camera-feed"></video>
                <button className="capture-btn" onClick={capturePhoto} disabled={loading}>
                  {loading ? 'Processing...' : 'Capture & Identify'}
                </button>
              </>
            )}
          </div>
        </div>

        <div className="patient-info-card">
          <div className="patient-header">
            <h3 className={result?.match_found ? 'identified' : 'unknown'}>
              {result?.match_found ? result.name : 'Unknown'}
            </h3>
            {result?.match_found && result?.confidence !== undefined && (
              <div className="confidence-display">
                <div className="confidence-label">AI Confidence Score</div>
                <div className="confidence-container">
                  <div className="confidence-bar-wrapper">
                    <div 
                      className={`confidence-bar ${
                        result.confidence >= 0.8 ? 'high' : 
                        result.confidence >= 0.6 ? 'medium' : 'low'
                      }`}
                      style={{ width: `${(result.confidence * 100)}%` }}
                    ></div>
                  </div>
                  <span className={`confidence-percentage ${
                    result.confidence >= 0.8 ? 'high' : 
                    result.confidence >= 0.6 ? 'medium' : 'low'
                  }`}>
                    {Math.round(result.confidence * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>
          <div className="info-fields">
            <div className="info-field">
              <span className="field-label">Age:</span>
              <span className="field-value">{result?.patient_info?.age || '-'}</span>
            </div>
            <div className="info-field">
              <span className="field-label">Sex:</span>
              <span className="field-value">{result?.patient_info?.sex || '-'}</span>
            </div>
            <div className="info-field">
              <span className="field-label">Height:</span>
              <span className="field-value">{result?.patient_info?.height || '-'}</span>
            </div>
            <div className="info-field">
              <span className="field-label">Weight:</span>
              <span className="field-value">{result?.patient_info?.weight || '-'}</span>
            </div>
            <div className="info-field">
              <span className="field-label">Insurance:</span>
              <span className="field-value">{result?.patient_info?.insurance || '-'}</span>
            </div>
            <div className="info-field">
              <span className="field-label">Allergies:</span>
              <span className="field-value">
                {result?.patient_info?.allergies?.length > 0 
                  ? result.patient_info.allergies.join(', ') 
                  : '-'}
              </span>
            </div>
            <div className="info-field">
              <span className="field-label">Medical History:</span>
              <span className="field-value">
                {result?.patient_info?.conditions?.length > 0 
                  ? result.patient_info.conditions.join(', ') 
                  : '-'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  const renderAddPatient = () => (
    <div className="add-patient-page">
      <div className="page-header">
        <h2>Add Patient</h2>
        <p className="page-description">
          Add a patient into the database, filling in relevant information and a face scan.
        </p>
      </div>

      <div className="add-patient-content">
        <div className="photo-section">
          <h3>Patient Photo</h3>
          <div className="photo-capture-area">
            {addPreview ? (
              <div className="photo-preview">
                <img src={addPreview} alt="Patient" />
                <button className="retake-photo-btn" onClick={() => {
                  setAddPreview(null)
                  setSelectedImage(null)
                  startAddPatientCamera()
                }}>
                  Retake Photo
                </button>
              </div>
            ) : (
              <div className="camera-container-add-patient">
                <video ref={addPatientVideoRef} autoPlay playsInline className="camera-feed-add-patient"></video>
                <button className="capture-photo-btn" onClick={captureAddPatientPhoto}>
                  Capture Photo
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="form-section">
          <h3>Patient Information</h3>
          <div className="form-fields">
            <div className="form-field">
              <label>Name:</label>
              <input
                type="text"
                value={patientData.name}
                onChange={(e) => setPatientData({...patientData, name: e.target.value})}
                placeholder="Enter patient name"
              />
            </div>
            <div className="form-field">
              <label>Age:</label>
              <input
                type="text"
                value={patientData.age}
                onChange={(e) => setPatientData({...patientData, age: e.target.value})}
                placeholder="Enter age"
              />
            </div>
            <div className="form-field">
              <label>Sex:</label>
              <input
                type="text"
                value={patientData.sex}
                onChange={(e) => setPatientData({...patientData, sex: e.target.value})}
                placeholder="Enter sex"
              />
            </div>
            <div className="form-field">
              <label>Height:</label>
              <input
                type="text"
                value={patientData.height}
                onChange={(e) => setPatientData({...patientData, height: e.target.value})}
                placeholder="Enter height"
              />
            </div>
            <div className="form-field">
              <label>Weight:</label>
              <input
                type="text"
                value={patientData.weight}
                onChange={(e) => setPatientData({...patientData, weight: e.target.value})}
                placeholder="Enter weight"
              />
            </div>
            <div className="form-field">
              <label>Insurance:</label>
              <input
                type="text"
                value={patientData.insurance}
                onChange={(e) => setPatientData({...patientData, insurance: e.target.value})}
                placeholder="Enter insurance"
              />
            </div>
            <div className="form-field">
              <label>Allergies:</label>
              <input
                type="text"
                value={patientData.allergies}
                onChange={(e) => setPatientData({...patientData, allergies: e.target.value})}
                placeholder="Enter allergies"
              />
            </div>
            <div className="form-field">
              <label>Medical History:</label>
              <textarea
                value={patientData.conditions}
                onChange={(e) => setPatientData({...patientData, conditions: e.target.value})}
                placeholder="Enter medical history"
                rows="3"
              />
            </div>
            <button className="submit-btn" onClick={handleAddPatient}>
              Add Patient
        </button>
          </div>
        </div>
      </div>
    </div>
  )

  const getCurrentPatientIndex = () => {
    if (!selectedPatient) return -1
    const filteredPatients = users.filter(patient =>
      patient.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    return filteredPatients.findIndex(p => p.id === selectedPatient.id)
  }

  const navigateToPrevious = () => {
    const filteredPatients = users.filter(patient =>
      patient.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    const currentIndex = getCurrentPatientIndex()
    if (currentIndex > 0) {
      setSelectedPatient(filteredPatients[currentIndex - 1])
    } else if (filteredPatients.length > 0) {
      // Wrap around to last patient
      setSelectedPatient(filteredPatients[filteredPatients.length - 1])
    }
  }

  const navigateToNext = () => {
    const filteredPatients = users.filter(patient =>
      patient.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    const currentIndex = getCurrentPatientIndex()
    if (currentIndex < filteredPatients.length - 1) {
      setSelectedPatient(filteredPatients[currentIndex + 1])
    } else if (filteredPatients.length > 0) {
      // Wrap around to first patient
      setSelectedPatient(filteredPatients[0])
    }
  }

  const renderDatabase = () => {
    const filteredPatients = users.filter(patient =>
      patient.name.toLowerCase().includes(searchQuery.toLowerCase())
    )

    return (
      <div className="database-page">
        <div className="page-header">
          <h2>Database</h2>
          <p className="page-description">
            Add a patient into the database, filling in relevant information and a face scan.
          </p>
        </div>

        <div className="database-content">
          <div className="search-section">
            <label>Name:</label>
            <input 
              type="text" 
              placeholder="Search by name..." 
              className="search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="patients-grid">
            {filteredPatients.length === 0 ? (
              <div className="empty-state">
                <p>{searchQuery ? 'No patients found matching your search.' : 'No patients in database yet. Add patients using the "Add Patient" tab.'}</p>
              </div>
            ) : (
              filteredPatients.map((patient) => (
                <div 
                  key={patient.id} 
                  className="patient-card"
                  onClick={() => setSelectedPatient(patient)}
                >
                  <div className="patient-card-photo">
                    <img src={patient.photo} alt={patient.name} />
                  </div>
                  <div className="patient-card-info">
                    <h4>{patient.name}</h4>
                    <p>ID: {patient.id}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {selectedPatient && (() => {
          const filteredPatients = users.filter(patient =>
            patient.name.toLowerCase().includes(searchQuery.toLowerCase())
          )
          const currentIndex = filteredPatients.findIndex(p => p.id === selectedPatient.id)
          const hasPrevious = filteredPatients.length > 1
          const hasNext = filteredPatients.length > 1
          
          return (
            <div className="patient-modal-overlay" onClick={() => setSelectedPatient(null)}>
              <div className="patient-modal" onClick={(e) => e.stopPropagation()}>
                <button className="modal-close" onClick={() => setSelectedPatient(null)}>×</button>
                {hasPrevious && (
                  <button 
                    className="modal-nav-btn modal-nav-left" 
                    onClick={(e) => {
                      e.stopPropagation()
                      navigateToPrevious()
                    }}
                    aria-label="Previous patient"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                  </button>
                )}
                {hasNext && (
                  <button 
                    className="modal-nav-btn modal-nav-right" 
                    onClick={(e) => {
                      e.stopPropagation()
                      navigateToNext()
                    }}
                    aria-label="Next patient"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                )}
                <div className="modal-content">
                <div className="modal-photo-section">
                  <img src={selectedPatient.photo} alt={selectedPatient.name} />
                </div>
                <div className="modal-info-section">
                  <h2>{selectedPatient.name}</h2>
                  <div className="modal-info-grid">
                    <div className="modal-info-item">
                      <span className="modal-label">Patient ID:</span>
                      <span className="modal-value">{selectedPatient.id}</span>
                    </div>
                    <div className="modal-info-item">
                      <span className="modal-label">Age:</span>
                      <span className="modal-value">{selectedPatient.age}</span>
                    </div>
                    <div className="modal-info-item">
                      <span className="modal-label">Sex:</span>
                      <span className="modal-value">{selectedPatient.sex}</span>
                    </div>
                    <div className="modal-info-item">
                      <span className="modal-label">Height:</span>
                      <span className="modal-value">{selectedPatient.height}</span>
                    </div>
                    <div className="modal-info-item">
                      <span className="modal-label">Weight:</span>
                      <span className="modal-value">{selectedPatient.weight}</span>
                    </div>
                    <div className="modal-info-item">
                      <span className="modal-label">Insurance:</span>
                      <span className="modal-value">{selectedPatient.insurance}</span>
                    </div>
                    <div className="modal-info-item full-width">
                      <span className="modal-label">Allergies:</span>
                      <span className="modal-value">{selectedPatient.allergies || 'None'}</span>
                    </div>
                    <div className="modal-info-item full-width">
                      <span className="modal-label">Medical History:</span>
                      <span className="modal-value">{selectedPatient.conditions || 'No significant history'}</span>
                    </div>
                    <div className="modal-info-item">
                      <span className="modal-label">Date Added:</span>
                      <span className="modal-value">{selectedPatient.dateAdded}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          )
        })()}
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title" onClick={() => setActiveTab('live-scan')}>Identicare</h1>
        <nav className="app-nav">
          <button
            className={activeTab === 'live-scan' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setActiveTab('live-scan')}
          >
            Live Scan
          </button>
          <button
            className={activeTab === 'add-patient' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setActiveTab('add-patient')}
          >
            Add Patient
          </button>
          <button
            className={activeTab === 'database' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setActiveTab('database')}
          >
            Database
          </button>
        </nav>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <span>⚠️</span> {error}
          </div>
        )}

        {activeTab === 'live-scan' && renderLiveScan()}
        {activeTab === 'add-patient' && renderAddPatient()}
        {activeTab === 'database' && renderDatabase()}
      </main>
    </div>
  )
}

export default App
